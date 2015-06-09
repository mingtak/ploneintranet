from Acquisition import aq_inner
from plone.memoize.view import memoize
from zope.publisher.browser import BrowserView


class Apps(BrowserView):

    """ A view to serve as overview over apps
    """

    """ The tiles below are dummy tiles.
         Please do NOT implement real tiles here, put them in another package.
         We want to keep the theme simple and devoid of business logic
    """

    def __call__(self):
        """Render the default template"""
        context = aq_inner(self.context)
        self.target = context
        return super(Apps, self).__call__()

    @memoize
    def apps(self):
        ''' The list of my apps
        '''
        apps = []
        apps.append({
            'id': 'news',
            'title': 'News publisher',
            'url': self.context.absolute_url() + '/apps/news',
            'activities': [],
            'class': escape_id_to_class('news'),
            'icon': '/'.join([
                self.context.absolute_url(),
                '++theme++ploneintranet.theme/generated/apps/news/icon.svg'])
        })
        return apps


def escape_id_to_class(cid):
    """ We use workspace ids as classes to style them.
        if a workspace has dots in its name, this is not usable as a class
        name. We have to escape that. We might need to do more to them, so this
        became a utility function.
    """
    return cid.replace('.', '-')
