# cython: language_level=3
from multiprocessing.connection import Connection
ctypedef object DirEntry


cdef class AllWatcher:
    cdef:
        dict files
        str root_path

    cpdef bint should_watch_dir(self, DirEntry entry)
    cpdef bint should_watch_file(self, DirEntry entry)

    # TODO: is dir_path a str?
    cpdef void _walk(self, str dir_path, set changes, dict new_files) except *
    cpdef set check(self)

cdef class CompileWatcher(AllWatcher):
    cdef:
        object ignore_file
        object include_file
        object ignore_dir
        object temp_file_suffix


cdef class SearchPathsWatcher(AllWatcher):
    pass


cdef class MPScheduler:
    cdef list _pipe_snd  # List[Connection]
    cdef list _pipe_rcv  # List[Connection]
    cdef list _procs  # List[Process]
    cdef int num_processes
    cdef int _next_pipe_ndx

    cpdef void _target(self, str worker_id, object jobs: Connection)
    cdef void _spawn_procs(self)
    cdef void _kill_procs(self)
    cpdef void submit_one(self, object item)