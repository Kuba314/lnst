LNST in containers
^^^^^^^^^^^^^^^^^^
LNST supports running agents in containers at the host machine.
Containers and networks are dynamically created based on recipe requirements.
Containers are also automatically connected to networks.

Requirements
------------
The first requirement is **Podman**, follow installation steps on
`official Podman installation page <https://podman.io/getting-started/installation>`_.

Podman API is also required, follow the steps below:

Enabling Podman API service:
++++++++++++++++++++++++++++

.. code-block:: bash

    systemctl enable --now podman.socket

and get socket URL:

.. code-block:: bash

    systemctl status podman.socket | grep "Listen:"

Starting Podman API manually:
+++++++++++++++++++++++++++++
If you don't want to run Podman API as a service, you can start it manually.
Don't forget to run the command below with root privileges.

.. code-block:: bash

    podman system service --timeout 0 --log-level=debug

Socket URL could be found at the top of logs generated by this command.

The usual URL is `unix:/run/podman/podman.sock`

Build LNST agent image
----------------------
Currently, LNST does not support automated building, so build LNST agent
machine image.

Podman uses different `storage <https://docs.podman.io/en/latest/markdown/podman.1.html#root-value>`_ locations
for root-full and root-less images, so make sure
you build image to root-full storage.
LNST currently uses the default storage location.
Build context should be a directory, where your LNST project is located.

*Your local copy of LNST is used by agents in containers.*

Use -t argument to name your image, this name is later used.

.. code-block:: bash

    cd your_lnst_project_directory
    podman build . -t lnst -f container_files/Dockerfile


Now is everything ready to run LNST in containers.
For testing purposes, we can use `HelloWorldRecipe` from :ref:`hello-world-script`.

Only initialization of `Controller()` object has to be changed:

.. code-block:: python

    from lnst.Controller.MachineMapper import ContainerMapper
    from lnst.Controller.ContainerPoolManager import ContainerPoolManager

    podman_uri = ""  # podman URI from installation step above
    image_name = ""  # name of image from build step above
    ctl = Controller(poolMgr=ContainerPoolManager, mapper=ContainerMapper, podman_uri=podman_uri, image=image_name)


And run the script.

Classes documentation
---------------------
.. autoclass:: lnst.Controller.MachineMapper.ContainerMapper
    :members:


.. automodule:: lnst.Controller.ContainerPoolManager
    :members: ContainerPoolManager
