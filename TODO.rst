Todos
=====

In the lists below we mark with [R] the features that we consider necessary
for the 1.0 release of the app. We mark with [B] known bugs.

Common
------

- Add app icon and desktop integration.

Browsing part
-------------

- [R] Allow showing labels with file/directory names on thumbnails.

- [R] Move directory search on the orchestrator thread. This means directory
  layouts will be progressively created and we should be able to preview
  an incomplete layout (where one or more rows have been created but not
  all).

- [R] Remember sorting preferences.

- [RB] Recalculate browsing position when re-sorting, etc.

- [R] Caching of thumbnails.

- Handle better empty directories and directories with no images in them.
  Maybe show an "Empty directory" message? Or provide a button to switch on
  viewing the files?

- Better aesthetics for thumbnails and various icons: directory thumbnails
  could use gradients to mark the border between adjacent images. Nicer icons
  for loading thumbnail, ordinary directory, broken image or ordinary file.

Viewer part
-----------

- [R] Keep image position when scaling.

- Keep scale intention (exponent) and allow reusing it when going to next
  prev image.

- Scale to fit and fill screen.

- Refine navigation with mouse, with keyboard, with touchpad.

- Allow to choose background for images with transparency and automatically
  choose the default.

Done
====

Browsing part
-------------

- [R] Rewrite directory thumbnail generation algorithm.

- [RB] Fix directory thumbnail for (transparent?) PNG (they appear white).

- [RB] Fix visualisation of small images (images for which the thumbnail is
  not smaller).
