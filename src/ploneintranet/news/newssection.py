from plone.dexterity.content import Item
from plone.directives import form
from zope.interface import implementer


class INewsApp(form.Schema):
    """
    Marker interface for NewsApp
    """


@implementer(INewsApp)
class NewsApp(Item):
    """
    A section to organize news items
    """
