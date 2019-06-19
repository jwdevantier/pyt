#include "wcsenc.h"
#include "string.h"
#include "stdlib.h"
#include "stdio.h"
#include "errno.h"

const size_t WCS_WRITE_ERROR = (size_t)-1;

struct wcsenc_s {
    mbstate_t state;
    char *buf;
    size_t bufsiz;
    size_t charlen;
};

wcsenc wcsenc_new(size_t charlen) {
    size_t bufsiz = (charlen + 1) * sizeof(wchar_t);
    void *buf = NULL;
    wcsenc_t *self = NULL;

    buf = (char *)malloc(bufsiz);
    if (buf == NULL) {
        perror("wcsenc_new: failed to allocate wcs buffer");
        return NULL;
    }

    self = (wcsenc_t *)malloc(sizeof(wcsenc_t));
    if (self == NULL) {
        free(buf);
        perror("wcsenc_new: failed to allocate wcsenc_t");
        return NULL;
    }

    memset(self, 0, sizeof(mbstate_t));
    self->buf = buf;
    self->bufsiz =  bufsiz;
    self->charlen = charlen;
    return self;
}

void wcsenc_free(wcsenc self) {
    if (self == NULL) {
        return;
    }
    if (self->buf != NULL) {
        free(self->buf);
    }
}

void wcsenc_reset(wcsenc self) {
    memset(self->buf, 0, sizeof(wchar_t));
    memset(&self->state, 0, sizeof(mbstate_t));
}

int wcsenc_realloc(wcsenc self, size_t charlen) {
    size_t bufsiz = (charlen + 1) * sizeof(wchar_t);
    void *new_buf = NULL;
    new_buf = realloc(self->buf, bufsiz);
    if (new_buf != NULL) {
        perror("wcsenc_realloc: failed to reallocate/expand buffer");
        return -1;
    }
    self->buf = new_buf;
    self->charlen = charlen;
    self->bufsiz = bufsiz;
    return 0;
}

size_t wcsenc_encode_wcs(wcsenc self, wchar_t *str, size_t len) {
    int realloc_ret = 0;
    size_t retval = (size_t)-1; // wcsrtombs returns this on error
    errno = 0;
    const wchar_t **ptr = (const wchar_t **)&str;
    if (len > self->charlen) {
        if ((realloc_ret = wcsenc_realloc(self, len))) {
            errno = ENOMEM;
            return retval;
        }
    }
    retval = wcsrtombs(self->buf, ptr, len * sizeof(wchar_t), &(self->state));
    if (errno) {
        perror("wcsenc_encode_wcs: failed to write encoded string to buffer");
    }
    return retval;
}

// TODO: figure out how to preserve inlining
size_t wcsenc_bufsiz(wcsenc self) {
    return self->bufsiz;
}

// TODO: figure out how to preserve inlining
char *wcsenc_buf(wcsenc self) {
    return self->buf;
}