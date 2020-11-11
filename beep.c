#include <err.h>
#include <stdarg.h>  // va_list (i don't actually know why the include has to be here)
#include <stdlib.h>  // EXIT_*
#include <unistd.h>  // openbsd pledge
#include <kcgi.h>

const static uint8_t gif[] = {
  0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,0x80,0x01,0x00,0xc4,0x52,0xc8,0xff,0xff,0xff,0x21,0xfe,
  0x02,0x3c,0x33,0x00,0x2c,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,0x44,0x01,0x00,0x3b,0x0a,
};

static void pixel(struct kreq *r) {
  khttp_head(r, kresps[KRESP_STATUS], "%s", khttps[KHTTP_200]);
  khttp_head(r, kresps[KRESP_CONTENT_TYPE], "%s", kmimetypes[KMIME_IMAGE_GIF]);
  khttp_head(r, "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
  khttp_head(r, "Pragma", "no-cache");
  khttp_body(r);
  khttp_write(r, gif, sizeof(gif));
  khttp_free(r);
}

int main(void) {
  struct kreq r;
  struct kfcgi *fcgi;

  if (khttp_fcgi_init(&fcgi, NULL, 0, NULL, 0, 0) != KCGI_OK)
    err(EXIT_FAILURE, "khttp init");

  if (pledge("proc recvfd sendfd stdio unix", NULL) == -1)
    err(EXIT_FAILURE, "pledge");  // see kcgi(3) Pledge Promises

  while (khttp_fcgi_parse(fcgi, &r) == KCGI_OK)
    pixel(&r);

  khttp_fcgi_free(fcgi);
  return EXIT_SUCCESS;
}
