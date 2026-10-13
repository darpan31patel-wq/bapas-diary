# Face models

Used by `make.py` to find Bapa in each photo so the crop never cuts him out.

- `face_detection_yunet_2023mar.onnx`: YuNet face detector, from [opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) (MIT licence).
- `face_recognition_sface_2021dec.onnx`: SFace face recogniser, from [opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) (Apache 2.0 licence).
- `bapa-faces.json`: Bapa's face as two averaged SFace fingerprints, `psm` (Pramukh Swami Maharaj, built from 60 photos)
  and `msm` (Mahant Swami Maharaj, built from 90 photos), taken from the 12 and 13 October On This Day photos.
  A face counts as Bapa when its similarity is at least 0.5; other people and murtis score below about 0.35.
