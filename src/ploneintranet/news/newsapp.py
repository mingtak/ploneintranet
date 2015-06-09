from plone.dexterity.content import Container
from plone.directives import form
from plone.namedfile.interfaces import IImageScaleTraversable
from ploneintranet.attachments.attachments import IAttachmentStoragable
from zope.interface import implementer


class INewsApp(form.Schema, IImageScaleTraversable):
    """
    Marker interface for NewsApp
    """


@implementer(INewsApp, IAttachmentStoragable)
class NewsApp(Container):
    """
    A folder to contain NewsFolders
    """
