AIT DSN Installation
======================

This guide will show you how to install AIT DSN. It assumes that you have followed the `AIT Core Installation and Configuration Guide <https://ait-core.readthedocs.io/en/latest/installation.html>`_ and ended up with a working AIT Core install. You can install AIT DSN from a checkout of the code or from PyPi. Having a checkout of the code can be handy if you want to view the source or make changes. Installing from PyPi keeps your system clutter free since you don't have a copy of the code base around. Either choice will work fine!

From Code Checkout
------------------

Clone the repository Github

.. code-block:: bash

   > git clone https://github.com/NASA-AMMOS/AIT-DSN.git
   > cd AIT-DSN

Find the latest tagged version of the code and check it out

.. code-block:: bash

   > git tag
   > git checkout <Most recent version number output by the previous command>

Run the following to install AIT DSN:

.. code-block:: bash

   > pip install .

From AIT PyPi
---------------

.. code-block:: bash

   > pip install ait-dsn

Check Installation
------------------

Now that your installation has finished let's check that everything works as expected.

.. code-block:: bash

   # Test that you can properly import the ait.dsn package.
   > python -c "import ait.dsn"

If the last command **doesn't** generate any errors your installation is all set! If you see an error as shown below make sure to activate your virtual environment first.

.. code-block:: bash

   > python -c "import ait.dsn"
   Traceback (most recent call last):
     File "<string>", line 1, in <module>
   ImportError: No module named ait.dsn

Upgrading an Installation
-------------------------

When a new version of AIT DSN is released you'll most likely want to upgrade your environment. You'll need to upgrade differently depending on how you installed the system.

Installed from Code Checkout
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Navigate back to the directory where you checked out the code and run the following commands to pull the latest code, checkout the latest tag, and upgrade your install.

.. code-block:: bash

   > git checkout master
   > git pull
   > git tag
   > git checkout <Most recent version number output by the previous command>
   > pip install . --upgrade

Installed from PyPi
^^^^^^^^^^^^^^^^^^^

Run the following to upgrade to the latest AIT DSN (and AIT Core) versions.

.. code-block:: bash

   > pip install ait-dsn --upgrade
