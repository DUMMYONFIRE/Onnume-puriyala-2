from typing import Callable, List, Any
import cv2
import insightface
import threading

import roop.globals
import roop.processors.frame.core
from roop.core import update_status
from roop.face_analyser import get_one_face, get_many_faces, find_similar_face
from roop.face_reference import get_face_reference, set_face_reference, clear_face_reference
from roop.typing import Face, Frame
from roop.utilities import conditional_download, resolve_relative_path, is_image, is_video

FACE_SWAPPER = None
THREAD_LOCK = threading.Lock()
NAME = 'ROOP.FACE-SWAPPER'


def get_face_swapper() -> Any:
    global FACE_SWAPPER

    with THREAD_LOCK:
        if FACE_SWAPPER is None:
            model_path = resolve_relative_path('../models/inswapper_128.onnx')
            # Specify CUDA execution provider
            FACE_SWAPPER = insightface.model_zoo.get_model(model_path, providers=['CUDAExecutionProvider'])
    return FACE_SWAPPER


def clear_face_swapper() -> None:
    global FACE_SWAPPER

    FACE_SWAPPER = None


def pre_check() -> bool:
    download_directory_path = resolve_relative_path('../models')
    conditional_download(download_directory_path, ['https://huggingface.co/CountFloyd/deepfake/resolve/main/inswapper_128.onnx'])
    return True


def pre_start() -> bool:
    source_path = roop.globals.source_path
    target_path = roop.globals.target_path

    if not is_image(source_path):
        update_status('Select an image for source path.', NAME)
        return False

    source_image = cv2.imread(source_path)
    if not get_one_face(source_image):
        update_status('No face in the source image detected.', NAME)
        return False

    if not is_image(target_path) and not is_video(target_path):
        update_status('Select an image or video for target path.', NAME)
        return False

    return True


def post_process() -> None:
    clear_face_swapper()
    clear_face_reference()


def swap_face(source_face: Face, target_face: Face, temp_frame: Frame) -> Frame:
    return get_face_swapper().get(temp_frame, target_face, source_face, paste_back=True)


def process_frame(source_face: Face, reference_face: Face, temp_frame: Frame, update: Callable[[], None] = None) -> Frame:
    many_faces = get_many_faces(temp_frame) if roop.globals.many_faces else [find_similar_face(temp_frame, reference_face)]

    if many_faces:
        for target_face in many_faces:
            temp_frame = swap_face(source_face, target_face, temp_frame)
            if update:
                update()

    return temp_frame


def process_frames(source_path: str, temp_frame_paths: List[str], update: Callable[[], None]) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    reference_face = None if roop.globals.many_faces else get_face_reference()

    for temp_frame_path in temp_frame_paths:
        temp_frame = cv2.imread(temp_frame_path)
        result = process_frame(source_face, reference_face, temp_frame, update)
        cv2.imwrite(temp_frame_path, result)


def process_image(source_path: str, target_path: str, output_path: str) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    target_frame = cv2.imread(target_path)
    reference_face = None if roop.globals.many_faces else get_one_face(target_frame, roop.globals.reference_face_position)
    result = process_frame(source_face, reference_face, target_frame)
    cv2.imwrite(output_path, result)


def process_video(source_path: str, temp_frame_paths: List[str]) -> None:
    if not roop.globals.many_faces and not get_face_reference():
        reference_frame = cv2.imread(temp_frame_paths[roop.globals.reference_frame_number])
        reference_face = get_one_face(reference_frame, roop.globals.reference_face_position)
        set_face_reference(reference_face)

    roop.processors.frame.core.process_video(source_path, temp_frame_paths, process_frames)


def parse_args() -> None:
    # ... Your existing argument parsing logic ...


def limit_resources() -> None:
    # ... Your existing resource limiting logic ...


def update_status(message: str, scope: str = 'ROOP.CORE') -> None:
    # ... Your existing status updating logic ...


def destroy() -> None:
    # ... Your existing cleanup and exit logic ...


def start() -> None:
    # ... Your existing start logic ...


def run() -> None:
    # ... Your existing run logic ...


if __name__ == "__main__":
    parse_args()
    if not pre_check():
        sys.exit(1)
    for frame_processor in roop.processors.frame.core.get_frame_processors_modules(roop.globals.frame_processors):
        if not frame_processor.pre_check():
            sys.exit(1)
    limit_resources()
    if roop.globals.headless:
        start()
    else:
        window = roop.ui.init(start, destroy)
        window.mainloop()
