from Products.Five import BrowserView
from collective.workspace.interfaces import IWorkspace
from plone import api
from plone.memoize.view import memoize
from zope.interface import implements
from plone.app.blocks.interfaces import IBlocksTransformEnabled
from ploneintranet.workspace.interfaces import IWorkspaceState
from ploneintranet.workspace.utils import parent_workspace
from json import dumps


class BaseWorkspaceView(BrowserView):
    """
    Base view class for workspace related view
    """
    @memoize
    def workspace(self):
        """Acquire the root workspace of the current context"""
        return parent_workspace(self.context)

    def can_manage_workspace(self):
        """
        does this user have permission to manage the workspace
        """
        return api.user.has_permission(
            "ploneintranet.workspace: Manage workspace",
            obj=self.context,
        )

    def can_add_status_updates(self):
        """
        Does this user have the permission to add status updates
        """
        return api.user.has_permission(
            "Plone Social: Add Microblog Status Update",
            obj=self.context)


class WorkspaceView(BaseWorkspaceView):
    """
    Default View of the workspace
    """
    implements(IBlocksTransformEnabled)


class WorkspaceState(BaseWorkspaceView):
    """
    Information about the state of the workspace
    """

    implements(IWorkspaceState)

    @memoize
    def state(self):
        if self.workspace() is not None:
            return api.content.get_state(self.workspace())


class WorkspaceMembersJSONView(BrowserView):
    """
    Return member details in JSON

    TODO: consolidate WorkspaceMembersJSONView with AllUsersJSONView
    """
    def __call__(self):
        users = self.context.existing_users()
        member_details = []
        for user in users:
            member_details.append({
                'text': user['title'] or user['id'],
                'id': user['id'],
            })
        return dumps(member_details)


class AllUsersJSONView(BrowserView):
    """
    Return all users in JSON for use in picker
    TODO: consolidate WorkspaceMembersJSONView with AllUsersJSONView
    """
    def __call__(self):
        q = self.request.get('q', '')
        users = api.user.get_users()
        member_details = []
        for user in users:
            fullname = user.getProperty('fullname')
            email = user.getProperty('email')
            uid = user.getProperty('id')
            if q in fullname or q in email or q in uid:
                member_details.append({
                    'text': '%s <%s>' % (fullname, email),
                    'id': uid,
                })
        return dumps(member_details)


class AllGroupsJSONView(BrowserView):
    """
    Return all groups in JSON for use in picker
    TODO: consolidate AllGroupsJSONView with AllUsersJSONView
    """
    def __call__(self):
        q = self.request.get('q', '').lower()
        groups = api.group.get_groups()
        group_details = []
        ws = IWorkspace(self.context)
        for group in groups:
            groupid = group.getId()
            # XXX Filter out groups representing workspace roles. Review
            # whether we need/want this and/or can do it more efficiently.
            skip = False
            for special_group in ws.available_groups:
                if groupid.startswith('{}:'.format(special_group)):
                    skip = True
            if skip:
                continue
            title = group.getProperty('title') or groupid
            email = group.getProperty('email')
            if email:
                title = '%s <%s>' % (title, email)
            description = group.getProperty('description') or ''
            if q in title.lower() or q in description.lower():
                group_details.append({
                    'text': title,
                    'id': groupid,
                })
        return dumps(group_details)


class CaseWorkflowGuardView(BrowserView):
    """Enable transition to the next workflow state when there are no open
    tasks
    """

    @memoize
    def __call__(self):
        context = self.context
        catalog = api.portal.get_tool('portal_catalog')
        current_path = '/'.join(context.getPhysicalPath())
        brains = catalog(
            path=current_path,
            portal_type='todo',
            review_state='open',
        )
        has_no_open_tasks = len(brains) == 0
        return has_no_open_tasks
