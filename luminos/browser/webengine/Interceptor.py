from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
)


class UrlRequestInterceptor(QWebEngineUrlRequestInterceptor):

    def intercept_request(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl().toString()
        not_data_uri = 'data' != info.requestUrl().scheme()
        not_local_file = not info.requestUrl().isLocalFile()

        not_devtools = (
            not url.startswith('http://127.0.0.1') and not url.startswith('ws://127.0.0.1')
        )

        block_request = not_devtools and not_data_uri and not_local_file
        print("intercept request", url)
        info.block(False)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        self.intercept_request(info)
