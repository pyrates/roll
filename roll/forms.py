"""
Stolen from https://github.com/channelcat/sanic/blob/master/sanic/request.py
"""
from cgi import parse_header
from collections import namedtuple

File = namedtuple('File', ['type', 'body', 'name'])


class RequestParameters(dict):
    """Hosts a dict with lists as values where get returns the first
    value of the list and getlist returns the whole shebang
    """

    def get(self, name, default=None):
        """Return the first value, either the default or actual"""
        return super().get(name, [default])[0]

    def getlist(self, name, default=None):
        """Return the entire list"""
        return super().get(name, default)


def parse_multipart_form(body: bytes, boundary: bytes):
    """Parse a request body and returns fields and files

    :param body: bytes request body
    :param boundary: bytes multipart boundary
    :return: fields (RequestParameters), files (RequestParameters)
    """
    files = RequestParameters()
    fields = RequestParameters()

    form_parts = body.split(boundary)
    for form_part in form_parts[1:-1]:
        file_name = None
        file_type = None
        field_name = None
        line_index = 2
        line_end_index = 0
        while not line_end_index == -1:
            line_end_index = form_part.find(b'\r\n', line_index)
            form_line = form_part[line_index:line_end_index].decode('utf-8')
            line_index = line_end_index + 2

            if not form_line:
                break

            colon_index = form_line.index(':')
            form_header_field = form_line[0:colon_index].lower()
            form_header_value, form_parameters = parse_header(
                form_line[colon_index + 2:])

            if form_header_field == 'content-disposition':
                if 'filename' in form_parameters:
                    file_name = form_parameters['filename']
                field_name = form_parameters.get('name')
            elif form_header_field == 'content-type':
                file_type = form_header_value

        post_data = form_part[line_index:-4]
        if file_name or file_type:
            file_ = File(type=file_type, name=file_name, body=post_data)
            if field_name in files:
                files[field_name].append(file_)
            else:
                files[field_name] = [file_]
        else:
            value = post_data.decode('utf-8')
            if field_name in fields:
                fields[field_name].append(value)
            else:
                fields[field_name] = [value]

    return fields, files
