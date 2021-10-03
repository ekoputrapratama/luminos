project(
  'luminos',
  version: '0.1.0',
  license: 'MIT',
  meson_version: '>= 0.49.0',
)

lm_name = meson.project_name()

lm_prefix = get_option('prefix')
lm_bindir = get_option('bindir')
lm_datadir = get_option('datadir')
lm_libdir = get_option('libdir')

lm_pkgdatadir = lm_datadir / lm_name
lm_pkglibdir = lm_libdir / lm_name

lm_namespace = 'io.gitlab.Fisma.Luminos'

i18n = import('i18n')
gnome = import('gnome')
python = import('python').find_installation('python3')

# FIXME: workaround for missing path method
#        https://github.com/mesonbuild/meson/pull/4616
python_path = find_program('python3').path()

source_root = meson.current_source_dir()

data_dir = source_root / 'data'
po_dir = source_root / 'po'
src_dir = source_root / 'src'

pyrcc5 = find_program('pyrcc5')

run_command('pyrcc5', '-o', 'luminos/resources.py','data/resources.qrc')

subdir('data')
subdir('luminos')
# subdir('po')

meson.add_install_script('build-aux/postinstall.py')

