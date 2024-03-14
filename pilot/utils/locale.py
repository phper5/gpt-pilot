import gettext
import os

## msgfmt base.po  -o base.mo
def get_translator(domain='base'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    locale_parent_dir = os.path.dirname(current_dir)
    localedir = os.path.join(locale_parent_dir, 'locales')
    zh = gettext.translation('base', localedir=localedir, languages=['zh'])
    zh.install()
    return zh.gettext 