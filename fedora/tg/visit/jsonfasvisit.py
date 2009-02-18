'''
This plugin provides integration with the Fedora Account System using JSON
calls to the account system server.
'''

from turbogears import config
from turbogears.visit.api import Visit, BaseVisitManager

from fedora.client import ProxyClient

from fedora import _, __version__

import logging
log = logging.getLogger("turbogears.identity.jsonfasvisit")

class JsonFasVisitManager(BaseVisitManager):
    '''
    This proxies visit requests to the Account System Server running remotely.
    '''
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts')
    fas = None

    def __init__(self, timeout):
        self.debug = config.get('jsonfas.debug', False)
        if not self.fas:
            self.fas = ProxyClient(self.fas_url, session_as_cookie=False,
                    debug=self.debug,
                    session_name=config.get('visit.cookie.name', 'tg-visit'),
                    useragent='JsonFasVisitManager/%s' % __version__)
        BaseVisitManager.__init__(self, timeout)
        log.debug('JsonFasVisitManager.__init__: exit')

    def create_model(self):
        '''
        Create the Visit table if it doesn't already exist.

        Not needed as the visit tables reside remotely in the FAS2 database.
        '''
        pass

    def new_visit_with_key(self, visit_key):
        '''
        Return a new Visit object with the given key.
        '''
        log.debug('JsonFasVisitManager.new_visit_with_key: enter')
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        # We only need to get the session cookie from this request
        request_data = self.fas.send_request('',
                auth_params={'session_id': visit_key})
        session_id = request_data[0]
        log.debug('JsonFasVisitManager.new_visit_with_key: exit')
        return Visit(session_id, True)

    def visit_for_key(self, visit_key):
        '''
        Return the visit for this key or None if the visit doesn't exist or has
        expired.
        '''
        log.debug('JsonFasVisitManager.visit_for_key: enter')
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        # We only need to get the session cookie from this request
        request_data = self.fas.send_request('',
                auth_params={'session_id': visit_key})
        session_id = request_data[0]

        # Knowing what happens in turbogears/visit/api.py when this is called,
        # we can shortcircuit this step and avoid a round trip to the FAS
        # server.
        # if visit_key != session_id:
        #     # visit has expired
        #     return None
        # # Hitting FAS has already updated the visit.
        # return Visit(visit_key, False)
        log.debug('JsonFasVisitManager.visit_for_key: exit')
        if visit_key != session_id:
            return Visit(session_id, True)
        else:
            return Visit(visit_key, False)

    def update_queued_visits(self, queue):
        '''Update the visit information on the server'''
        log.debug('JsonFasVisitManager.update_queued_visits: enter')
        # Hit any URL in fas with each visit_key to update the sessions
        for visit_key in queue:
            log.info(_('updating visit (%s)'), visit_key)
            self.fas.send_request('', auth_params={'session_id': visit_key})
        log.debug('JsonFasVisitManager.update_queued_visits: exit')
