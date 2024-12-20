import cv2
cap1=cv2.VideoCapture("/dev/video0")
cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap2=cv2.VideoCapture("/dev/video2")
cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cap3=cv2.VideoCapture("/dev/video4")
cap3.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap3.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cap4=cv2.VideoCapture("/dev/video6")
cap4.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap4.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cap5=cv2.VideoCapture("/dev/video8")
cap5.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap5.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cap6=cv2.VideoCapture("/dev/video10")
cap6.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 设置宽度
cap6.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
while(1):
    ret,frame=cap1.read()
    cv2.imshow("cap1",frame)
    ret,frame=cap2.read()
    cv2.imshow("cap2",frame)
    ret,frame=cap3.read()
    cv2.imshow("cap3",frame)
    ret,frame=cap4.read()
    cv2.imshow("cap4",frame)

    ret,frame=cap5.read()
    cv2.imshow("cap5",frame)
    ret,frame=cap6.read()
    cv2.imshow("cap6",frame)
    cv2.waitKey(1)
