luminos_sources = files(
  '__init__.py',
  '__main__.py',
  'Application.py',
  'luminos.py',
  'resources.py'
)
python.install_sources(
  luminos_sources,
  subdir: 'luminos',
)

install_subdir('plugins',
  install_dir: lm_pkglibdir
)
subdir('browser')
subdir('core')
subdir('windows')
subdir('widgets')
subdir('utils')


