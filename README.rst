Glue SAMP plugin (experimental)
===============================

|Travis Status| |AppVeyor Status|

Requirements
------------

Note that this plugin requires `glue <http://glueviz.org/>`__ to be
installed - see `this
page <http://glueviz.org/en/latest/installation.html>`__ for
instructions on installing glue.

Installing
----------

If you are using conda, you can easily install the
plugin and all the required dependencies with::

    conda install -c glueviz glue-samp

Alternatively, if you don't use conda, be sure to install the above
dependencies then install the plugin with::

    pip install glue-samp

In both cases this will auto-register the plugin with Glue.

Testing
-------

To run the tests, do::

    py.test glue_samp

at the root of the repository. This requires the
`pytest <http://pytest.org>`__ module to be installed.

.. |Travis Status| image:: https://travis-ci.org/glue-viz/glue-samp.svg
   :target: https://travis-ci.org/glue-viz/glue-samp?branch=master
.. |AppVeyor Status| image:: https://ci.appveyor.com/api/projects/status/deue2c8puq7d9jkj/branch/master?svg=true
   :target: https://ci.appveyor.com/project/glue-viz/glue-samp/branch/master
