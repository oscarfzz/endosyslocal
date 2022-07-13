from paste.exceptions.errormiddleware import ErrorMiddleware
import logging, traceback, sys, pprint

log = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2)

class CustomErrorMiddleware(ErrorMiddleware):
    """
    Redirect exceptions to python logger.
    """
    def exception_handler(self, exc_info, env):
        # Logs the cgi & wsgi variables and the exception traceback
        log.error(pp.pformat(env), exc_info=True)
        # Continues with the normal behaviour of the ErrorMiddleware
        super(CustomErrorMiddleware, self).exception_handler(exc_info, env)