from lnst.Common.Parameters import (
    Param,
    IntParam,
    ListParam,
    StrParam,
    ChoiceParam,
)
from lnst.Common.IpAddress import AF_INET, AF_INET6

from lnst.RecipeCommon.Perf.Measurements import Flow as PerfFlow
from lnst.RecipeCommon.Perf.Measurements import IperfFlowMeasurement, NeperFlowMeasurement

from lnst.Recipes.ENRT.MeasurementGenerators.BaseMeasurementGenerator import BaseMeasurementGenerator

from typing import List


MEASUREMENT_LOOKUP = {
    'iperf': IperfFlowMeasurement,
    'neper': NeperFlowMeasurement,
}

class FlowMeasurementGenerator(BaseMeasurementGenerator):
    """
    :param net_perf_tool:
        Parameter used by the :any:`generate_perf_configurations` generator to
        create a PerfRecipeConf object.
        Specifies a string name that maps to a network flow measurement class
        that accepts :any:`PerfFlow` objects and can be used to measure those specified flows.
        Supported options are 'iperf' or 'neper'
    :type net_perf_tool: :any:`ChoiceParam` (default 'iperf' )

    :param perf_tests:
        Parameter used by the :any:`generate_flow_combinations` generator.
        Tells the generator what types of network flow measurements to generate
        perf test configurations for.
    :type perf_tests: Tuple[str] (default ("tcp_stream", "udp_stream",
        "sctp_stream"))

    :param perf_tool_cpu:
        Parameter used by the :any:`generate_flow_combinations` generator. To
        indicate that the flow measurement should be pinned to a specific CPU
        core.
    :type perf_tool_cpu: :any:`IntParam` (optional parameter)

    :param perf_tool_cpu_policy:
        Allows user to control how the cpus specified through the `perf_tool_cpu`
        parameter are assigned to instances of the performance measurement tool.

        This parameter is usually used when `perf_parallel_processes` is set to a value greater than one.
        The value can be:
         * `round-robin` - each of the processes will be pinned to exactly ONE cpu from the list defined by perf_tool_cpu in round-robin fashion
         * `all` - each of the processes will be pinned to all cpus in the list defined by perf_tool_cpu
    :type perf_tool_cpu_policy: :any:`StrParam` (default `all`)

    :param perf_duration:
        Parameter used by the :any:`generate_perf_configurations` generator. To
        specify the duration of the performance measurements, in seconds.
    :type perf_duration: :any:`IntParam` (default 60)

    :param perf_iterations:
        Parameter used by the :any:`generate_perf_configurations` generator. To
        specify how many times should each performance measurement be repeated
        to generate cumulative results which can be statistically analyzed.
    :type perf_iterations: :any:`IntParam` (default 5)

    :param perf_parallel_streams:
        Parameter used by the :any:`generate_flow_combinations` generator. To
        specify how many parallel streams of the same network flow should be
        measured at the same time.
    :type perf_parallel_streams: :any:`IntParam` (default 1)

    :param perf_parallel_processes:
        Parameter used by the :any:`generate_flow_combinations` generator. To
        specify how many parallel net_perf_tool processes of the same network flow
        should be measured at the same time.
    :type perf_parallel_processes: :any:`IntParam` (default 1)

    :param perf_msg_sizes:
        Parameter used by the :any:`generate_flow_combinations` generator. To
        specify what different message sizes (in bytes) used generated for the
        network flow should be tested - each message size resulting in a
        separate performance measurement.
    :type perf_msg_sizes: List[Int] (default [123])
    """

    # common perf test params
    perf_tests = Param(default=("tcp_stream", "udp_stream", "sctp_stream"))
    perf_tool_cpu = ListParam(mandatory=False)
    perf_tool_cpu_policy = StrParam(mandatory=False)
    perf_duration = IntParam(default=60)
    perf_iterations = IntParam(default=5)
    perf_parallel_streams = IntParam(default=1)
    perf_parallel_processes = IntParam(default=1)
    perf_msg_sizes = ListParam(default=[123])

    net_perf_tool = ChoiceParam(type=StrParam, choices=MEASUREMENT_LOOKUP.keys(), default='iperf')

    @property
    def net_perf_tool_class(self):
        cls = self.params.get('net_perf_tool', None)
        if cls is None:
            return IperfFlowMeasurement
        else:
            return MEASUREMENT_LOOKUP[cls]

    def generate_perf_measurements_combinations(self, config):
        combinations = super().generate_perf_measurements_combinations(config)
        for flow_combination in self.generate_flow_combinations(config):
            combinations.append([self.net_perf_tool_class(flow_combination)])
        return combinations

    def generate_flow_combinations(self, config):
        """Base flow combination generator

        The generator loops over all endpoint pairs to test performance between
        (generated by the :any:`generate_perf_endpoints` method) then over all
        the selected :any:`ip_versions` and uses the first IP address fitting
        these criteria. Then the generator loops over the selected performance
        tests as selected via :any:`perf_tests`, then message sizes from
        :any:`msg_sizes`.

        :return: list of Flow combinations to measure in parallel
        :rtype: List[:any:`PerfFlow`]
        """
        for client_nic, server_nic in self.generate_perf_endpoints(config):
            for ipv in self.params.ip_versions:
                ip_filter = {}
                if ipv == "ipv4":
                    ip_filter.update(family=AF_INET)
                elif ipv == "ipv6":
                    ip_filter.update(family=AF_INET6)
                    ip_filter.update(is_link_local=False)

                client_bind = client_nic.ips_filter(**ip_filter)[0]
                server_bind = server_nic.ips_filter(**ip_filter)[0]

                for perf_test in self.params.perf_tests:
                    for size in self.params.perf_msg_sizes:
                        yield self._create_perf_flows(
                            perf_test,
                            client_nic,
                            client_bind,
                            server_nic,
                            server_bind,
                            size,
                        )

    def generate_perf_endpoints(self, config):
        """Generator for perf endpoints

        To be overridden by a derived class.

        :return: list of device pairs
        :rtype: List[Tuple[:any:`Device`, :any:`Device`]]
        """
        return []

    def _create_perf_flows(
        self,
        perf_test,
        client_nic,
        client_bind,
        server_nic,
        server_bind,
        msg_size,
    ) -> List[PerfFlow]:
        flows = []
        port_offset=12000
        for i in range(self.params.perf_parallel_processes):
            flows.append(
                self._create_perf_flow(
                    perf_test,
                    client_nic,
                    client_bind,
                    server_nic,
                    server_bind,
                    port_offset + i,
                    msg_size,
                    self._cpupin_based_on_policy(i),
                )
            )

        return flows

    def _cpupin_based_on_policy(self, process_no=None):
        if process_no is None:
            return None

        try:
            cpus = self.params.perf_tool_cpu
        except:
            return None

        try:
            policy = self.params.perf_tool_cpu_policy
        except:
            return cpus

        if policy == 'round-robin':
            return [cpus[process_no % len(cpus)]]
        elif policy == 'all':
            return cpus
        else:
            raise Exception(f'Unknown perf_tool_cpu_policy {policy}')

    def _create_perf_flow(
        self,
        perf_test,
        client_nic,
        client_bind,
        server_nic,
        server_bind,
        server_port,
        msg_size,
        cpupin,
    ) -> PerfFlow:
        """
        Wrapper to create a PerfFlow. Mixins that want to change this behavior (for example, to reverse the direction)
        can override this method as an alternative to overriding :any:`generate_flow_combinations`
        """
        return PerfFlow(
            type=perf_test,
            generator=client_nic.netns,
            generator_bind=client_bind,
            generator_nic=client_nic,
            receiver=server_nic.netns,
            receiver_bind=server_bind,
            receiver_nic=server_nic,
            receiver_port=server_port,
            msg_size=msg_size,
            duration=self.params.perf_duration,
            parallel_streams=self.params.perf_parallel_streams,
            cpupin=cpupin,
        )
