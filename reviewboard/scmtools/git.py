from __future__ import unicode_literals

from django.utils import six
from django.utils.six.moves.urllib.parse import quote as urlquote
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         InvalidRevisionFormatError,
                                         RepositoryNotFoundError,
                                         SCMError)


try:
    import urlparse
    uses_netloc = urlparse.uses_netloc
    urllib_urlparse = urlparse.urlparse
except ImportError:
    import urllib.parse
    uses_netloc = urllib.parse.uses_netloc
    urllib_urlparse = urllib.parse.urlparse
uses_netloc.append('git')

            detail=six.text_type(_('The SHA1 is too short. Make sure the diff '
                                   'is generated with `git diff '
                                   '--full-index`.')),
        'path': _('For local Git repositories, this should be the path to a '
                  '.git directory that Review Board can read from. For remote '
                  'Git repositories, it should be the clone URL.'),
    pre_creation_regexp = re.compile(b"^0+$")
        preamble = b''
                    preamble = b''
                preamble = b''
                preamble += self.lines[i] + b'\n'
        if not self.files and preamble.strip() != b'':
            # This is probably not an actual git diff file.
            raise DiffParserError('This does not appear to be a git diff', 0)

        if self.lines[linenum].startswith(b"diff --git"):
        file_info.data = self.lines[linenum] + b'\n'
        # We split at the b/ to deal with space in filenames
        diff_line = self.lines[linenum].split(b' b/')
            file_info.origFile = diff_line[-2].replace(b'diff --git a/', b'')
            file_info.newFile = diff_line[-1]

            if isinstance(file_info.origFile, six.binary_type):
                file_info.origFile = file_info.origFile.decode('utf-8')

            if isinstance(file_info.newFile, six.binary_type):
                file_info.newFile = file_info.newFile.decode('utf-8')
        # Check to make sure we haven't reached the end of the diff.
        if linenum >= len(self.lines):
            return linenum, None

            file_info.data += self.lines[linenum] + b"\n"
            file_info.data += self.lines[linenum] + b"\n"
            file_info.data += self.lines[linenum] + b"\n"
            file_info.data += self.lines[linenum + 1] + b"\n"
            file_info.data += self.lines[linenum] + b"\n"
            file_info.data += self.lines[linenum + 1] + b"\n"
            file_info.data += self.lines[linenum + 2] + b"\n"
            file_info.data += self.lines[linenum] + b"\n"
            file_info.data += self.lines[linenum + 1] + b"\n"
            file_info.data += self.lines[linenum + 2] + b"\n"
        # Assume by default that the change is empty. If we find content
        # later, we'll clear this.
        empty_change = True
            file_info.data += self.lines[linenum] + b"\n"
                break
            elif self._is_binary_patch(linenum):
                file_info.data += self.lines[linenum] + b"\n"
                empty_change = False
                linenum += 1
                break
            elif self._is_diff_fromfile_line(linenum):
                if self.lines[linenum].split()[1] == b"/dev/null":
                file_info.data += self.lines[linenum] + b'\n'
                file_info.data += self.lines[linenum + 1] + b'\n'
                linenum += 2
            else:
                empty_change = False
                linenum = self.parse_diff_line(linenum, file_info)

        # For an empty change, we keep the file's info only if it is a new
        # 0-length file, a moved file, a copied file, or a deleted 0-length
        # file.
        if (empty_change and
            file_info.origInfo != PRE_CREATION and
            not (file_info.moved or file_info.copied or file_info.deleted)):
            # We didn't find any interesting content, so leave out this
            # file's info.
            #
            # Note that we may want to change this in the future to preserve
            # data like mode changes, but that will require filtering out
            # empty changes at the diff viewer level in a sane way.
            file_info = None
        return self.lines[linenum].startswith(b"new file mode")
        return self.lines[linenum].startswith(b"deleted file mode")
        return (self.lines[linenum].startswith(b"old mode")
                and self.lines[linenum + 1].startswith(b"new mode"))
        return (self.lines[linenum].startswith(b'similarity index') and
                self.lines[linenum + 1].startswith(b'copy from') and
                self.lines[linenum + 2].startswith(b'copy to'))
        return (self.lines[linenum].startswith(b"similarity index") and
                self.lines[linenum + 1].startswith(b"rename from") and
                self.lines[linenum + 2].startswith(b"rename to"))
                self.lines[linenum].startswith(b"index "))
        return self.lines[linenum].startswith(b'diff --git')
        return (line.startswith(b"Binary file") or
                line.startswith(b"GIT binary patch"))
                (self.lines[linenum].startswith(b'--- ') and
                    self.lines[linenum + 1].startswith(b'+++ ')))
        """Make sure that the file object has all expected fields.
        This is needed so that there aren't explosions higher up the chain when
        the web layer is expecting a string object.
                setattr(file_info, attr, b'')
        url_parts = urllib_urlparse(self.path)
        url = url.replace("<filename>", urlquote(path))
        errmsg = six.text_type(p.stderr.read())
                raise SCMError("path must be supplied if revision is %s"
                               % HEAD)
            return six.text_type(revision)
        url_parts = urllib_urlparse(path)