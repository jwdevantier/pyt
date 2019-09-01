from hashlib import md5

cpdef str file_hash(str path: str, size_t chunksiz=65536):
    cdef:
        bytes buf
    hasher = md5()
    with open(path, 'rb') as fh:
        buf = fh.read(chunksiz)
        while buf:
            hasher.update(buf)
            buf = fh.read(chunksiz)
    return hasher.hexdigest()
