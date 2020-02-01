# cython: language_level=3
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
