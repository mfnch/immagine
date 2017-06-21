Todos
=====

In the lists below we mark with [R] the features that we consider necessary
for the 1.0 release of the app. We mark with [B] known bugs.

Browsing part
-------------

- [R] Allow showing labels with file/directory names on thumbnails.

- [R] Move directory search on the orchestrator thread. This means directory
  layouts will be progressively created and we should be able to preview
  an incomplete layout (where one or more rows have been created but not
  all).

- [RB] Fix visualisation of small images (images for which the thumbnail is
  not smaller).

- [RB] Fix directory thumbnail for (transparent?) PNG (they appear white).

- [R] Remember sorting preferences.

- [RB] Recalculate browsing position when re-sorting, etc.

- [R] Caching of thumbnails.

Viewer part
-----------

- [R] Keep image position when scaling.

- Keep scale intention (exponent) and allow reusing it when going to next
  prev image.

- Scale to fit and fill screen.

- Refine navigation with mouse, with keyboard, with touchpad.

Done
====

Browsing part
-------------

- [R] Rewrite directory thumbnail generation algorithm.
