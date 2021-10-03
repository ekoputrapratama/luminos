"""Various utilities shared between webpage/webview subclasses."""

import html

from PyQt5.QtCore import QUrl

from luminos.utils import log, usertypes, message


class CallSuper(Exception):
    """Raised when the caller should call the superclass instead."""


def javascript_confirm(url, js_msg, abort_on, *, escape_msg=True):
    """Display a javascript confirm prompt."""
    log.js.debug("confirm: {}".format(js_msg))

    js_msg = html.escape(js_msg) if escape_msg else js_msg
    msg = 'From <b>{}</b>:<br/>{}'.format(html.escape(url.toDisplayString()),
                                          js_msg)
    urlstr = url.toString(QUrl.RemovePassword | QUrl.FullyEncoded)
    ans = message.ask('Javascript confirm', msg,
                      mode=usertypes.PromptMode.yesno,
                      abort_on=abort_on, url=urlstr)
    return bool(ans)


def javascript_prompt(url, js_msg, default, abort_on, *, escape_msg=True):
    """Display a javascript prompt."""
    log.js.debug("prompt: {}".format(js_msg))

    js_msg = html.escape(js_msg) if escape_msg else js_msg
    msg = '<b>{}</b> asks:<br/>{}'.format(html.escape(url.toDisplayString()),
                                          js_msg)
    urlstr = url.toString(QUrl.RemovePassword | QUrl.FullyEncoded)
    answer = message.ask('Javascript prompt', msg,
                         mode=usertypes.PromptMode.text,
                         default=default,
                         abort_on=abort_on, url=urlstr)

    if answer is None:
        return (False, "")
    else:
        return (True, answer)


def javascript_alert(url, js_msg, abort_on, *, escape_msg=True):
    """Display a javascript alert."""
    log.js.debug("alert: {}".format(js_msg))

    js_msg = html.escape(js_msg) if escape_msg else js_msg
    msg = 'From <b>{}</b>:<br/>{}'.format(html.escape(url.toDisplayString()),
                                          js_msg)
    urlstr = url.toString(QUrl.RemovePassword | QUrl.FullyEncoded)
    message.ask('Javascript alert', msg, mode=usertypes.PromptMode.alert,
                abort_on=abort_on, url=urlstr)


def javascript_log_message(level, source, line, msg):
    """Display a JavaScript log message."""
    logstring = "[{}:{}] {}".format(source, line, msg)
    # Needs to line up with the values allowed for the
    # content.javascript.log setting.
    # logmap = {
    #     'none': lambda arg: None,
    #     'debug': log.js.debug,
    #     'info': log.js.info,
    #     'warning': log.js.warning,
    #     'error': log.js.error,
    # }
    logger = None
    if level == usertypes.JsLogLevel.info:
        logger = log.js.info
    if level == usertypes.JsLogLevel.warning:
        logger = log.js.warning
    if level == usertypes.JsLogLevel.error:
        logger = log.js.error

    logger(logstring)
