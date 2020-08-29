from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy as np

setup(name='Hello world app',
      ext_modules=cythonize(Extension(
            'cgini',
            sources=['cgini.pyx'],
            include_dirs=[np.get_include()]
      )))
