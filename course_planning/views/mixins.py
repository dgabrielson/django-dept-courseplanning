import base64
import mimetypes

from django.http import Http404, HttpResponse

################################################################


class SessionFileViewMixin(object):
    """
    Use this mixin for stashing a generated file in the user session.
    """

    session_prefix = None

    def _get_session_prefix(self):
        if self.session_prefix is None:
            raise ImproperlyConfigured(
                "session_prefix is required for SessionFileMixin"
            )
        return self.session_prefix + "-"

    def _get_session_basekey(self):
        base = self._get_session_prefix() + "-"
        return base

    def construct_filename(self, basename, format):
        """
        So that the filename can be changed by overriding this method.
        """
        return basename + "." + format

    def set_session_result(self, basename, format, data):
        base = self._get_session_basekey()
        self.request.session[base + "filename"] = self.construct_filename(
            basename, format
        )
        if isinstance(data, bytes):
            self.request.session[base + "format"] = "b64"
            data = base64.b64encode(data).decode("utf-8")
        else:
            self.request.session[base + "format"] = None
        self.request.session[base + "data"] = data

    def _pop_session_result(self):
        base = self._get_session_basekey()
        filename = self.request.session.pop(base + "filename", None)
        data = self.request.session.pop(base + "data", None)
        format = self.request.session.pop(base + "format", None)
        if format == "b64":
            data = base64.b64decode(data)
        return filename, data

    def has_session_result(self):
        base = self._get_session_basekey()
        return (
            base + "filename" in self.request.session
            and base + "data" in self.request.session
        )

    def data_response(self, disposition_type=None):
        """
        ``disposition_type`` may be ``attachment``; which forces
        the view to download a file.
        """
        if not self.has_session_result():
            raise Http404("already downloaded")
        filename, data = self._pop_session_result()
        contenttype, encoding = mimetypes.guess_type(filename)
        response = HttpResponse(content_type=contenttype)
        content_disposition = ""
        if disposition_type is not None:
            content_disposition += disposition_type + "; "
        content_disposition += "filename=" + filename
        response["Content-Disposition"] = content_disposition
        response.write(data)
        return response


################################################################
