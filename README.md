# immagine
Image viewer with directory thumbnails and a focus on the browsing experience

## Status

This software is under development. It can already be used, but is not feature
complete. The user should expect bugs and misbehaviours here and there.
Please, have a look at the license file in this directory, LICENSE. Use at your
own risk! Contributions are welcome.

## Design considerations

This project was created due to the lack of an image viewer which suits my
personal needs. Below is a list of design considerations behind this project:

- Thumbnails are the most important feature while browsing a directory of
  images. All screen space should be used for thumbnails. Little screen space
  should be left unused.

- File names are typically uninteresting while browsing a directory of images.
  There is no need to waste screen space for them.

- Subdirectories should be thumbnailed as well. A directory thumbnail should
  be composed from the thumbnails of some representative images in it.

- The user should be given an opportunity of choosing the images used to
  compose the directory thumbnails.

- It may be desirable to show the names of subdirectories.

## Design choices

- Only Linux distros are targetted. No support for Windows or Mac OS is
  contemplated.

- The image viewer is written in Python and PyGTK is used for the GUI.
