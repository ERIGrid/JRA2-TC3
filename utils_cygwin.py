import errno
import ctypes
import sys


class CygpathError( Exception ):

    def __init__( self, errno, msg = '' ):
        self.errno = errno
        super( Exception, self ).__init__( os.strerror( errno ) )


class Cygpath( object ):

    bufsize = 1024

    cygpath_posix_to_win_a = 0 # From "char *posix" to "char *win32".
    cygpath_win_a_to_posix = 2 # From "char *win32" to "char *posix".

    def __init__( self ):
        if 'cygwin' not in sys.platform:
            raise SystemError( 'not running in Cygwin environment' )
        self._dll = ctypes.cdll.LoadLibrary( 'cygwin1.dll' )

    def _cygwin_conv_path( self, what, path, size = None ):
        if size is None:
            size = self.bufsize
        out = ctypes.create_string_buffer( size )
        ret = self._dll.cygwin_conv_path( what, path, out, size )
        if ret < 0:
            raise CygpathError( ctypes.get_errno() )
        return out.value

    def posix2win( self, path ):
        return self._cygwin_conv_path( self.cygpath_posix_to_win_a, str( path ) )

    def win2posix( self, path ):
        return self._cygwin_conv_path( self.cygpath_win_a_to_posix, str( path ) )
