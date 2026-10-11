#ifndef ASTRA_RENDER_STATUS_H
#define ASTRA_RENDER_STATUS_H
#include "render.h"
#include "ui_status.h"

UBYTE renderStatusCreate(tVPort *port);
/* Call immediately after vblank acknowledgement, before any rendering work.
 * Only this bottom-raster reservation can update a retained front copper list. */
void renderStatusUpdate(tUiStatus status, tLanguage language);
void renderStatusDestroy(void);
#endif
