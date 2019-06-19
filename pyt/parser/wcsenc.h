#ifndef WCSENC_H
#define WCSENC_H

#include "wchar.h"

struct wcsenc_s;
typedef struct wcsenc_s wcsenc_t; 
typedef wcsenc_t *wcsenc;

wcsenc wcsenc_new(size_t charlen);
void wcsenc_free(wcsenc self);
void wcsenc_reset(wcsenc self);
size_t wcsenc_encode_wcs(wcsenc self, wchar_t *str, size_t len);
// TODO: figure out how to preserve inlining
size_t wcsenc_bufsiz(wcsenc self);
// TODO: figure out how to preserve inlining
char *wcsenc_buf(wcsenc self);

extern const size_t WCS_WRITE_ERROR;

#endif