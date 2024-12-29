import cv2
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait

def save_single_camera(camera_id, timestamp, main_cap=None):
    """单个相机保存图片的函数"""
    try:
        if camera_id == 0 and main_cap is not None:
            print(f"保存摄像头 {camera_id} 的图片...")
            ret, frame = main_cap.read()
            if ret:
                filename = f"camera_{camera_id}_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"已保存 {filename}")
                return True
            return False

        print(f"保存摄像头 {camera_id} 的图片...")
        cap = cv2.VideoCapture(f'/dev/video{camera_id}')
        if not cap.isOpened():
            print(f"无法打开摄像头 {camera_id}")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        if ret:
            filename = f"camera_{camera_id}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"已保存 {filename}")
            success = True
        else:
            print(f"无法从摄像头 {camera_id} 读取图像")
            success = False

        cap.release()
        return success

    except Exception as e:
        print(f"保存摄像头 {camera_id} 图片时出错: {e}")
        return False

def save_all_cameras(main_cap):
    """同时保存所有相机的图片"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    camera_ids = [0, 2, 4, 6, 8, 10]
    
    with ThreadPoolExecutor(max_workers=len(camera_ids)) as executor:
        future_to_camera = {
            executor.submit(save_single_camera, 
                          camera_id, 
                          timestamp,
                          main_cap if camera_id == 0 else None): camera_id
            for camera_id in camera_ids
        }
        wait(future_to_camera.keys())

def main():
    # 打开主显示用的摄像头
    main_cap = cv2.VideoCapture('/dev/video0')
    if not main_cap.isOpened():
        print("无法打开主摄像头")
        return

    # 设置采集分辨率
    main_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    main_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 设置显示窗口名称和大小
    window_name = 'Camera'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)  # 设置显示窗口大小

    print("程序已启动:")
    print("按's'键同时保存所有摄像头的图片")
    print("按'q'键退出程序")

    while True:
        ret, frame = main_cap.read()
        if ret:
            # 调整显示尺寸
            display_frame = cv2.resize(frame, (640, 480))
            cv2.imshow(window_name, display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print("\n开始保存图片...")
            save_all_cameras(main_cap)
            print("保存完成\n")
        elif key == ord('q'):
            break

    main_cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()