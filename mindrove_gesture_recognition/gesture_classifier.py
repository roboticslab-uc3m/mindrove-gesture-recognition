import socket
import statistics
from collections import deque
from statistics import mean

import joblib
import numpy as np
import pandas as pd
import rclpy
import sklearn
from rclpy.node import Node
from roboasset_msgs.msg import MindroveEmg
from std_msgs.msg import Int8


class GestureClassifier(Node):

    def __init__(self):
        super().__init__('gesture_classifier')
        self.subscription = self.create_subscription(
            MindroveEmg,
            'mindrove/emg',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning
        self.window_size = 10
        self.data_queue = deque([[0]*8]*self.window_size, maxlen=self.window_size)
        self.filename = 'src/mindrove_gesture_recognition/mindrove_gesture_recognition/svm2_model.sav'
        self.reg = joblib.load(self.filename)
        self.gesture = ["Idle","Thumb flexion","Index finger flexion","Middle finger flexion","Ring finger flexion","Pinky finger flexion","Wrist extension (outward)","Wrist flexion (inward)"]
        #max and min values specific for each user (YA MULTIPLICADOS *0.045)
        #this is for subject 1
        #self.maxval = np.array([17311.365, 16189.56, 22204.845, 12230.64, 13404.06, 16164.135, 3089.655, 20318.715])
        #self.minval = np.array([14016.555, 12871.215, 18823.005, 7769.43, 9877.23, 13195.17, 622.35, 17268.12])
        #this for subject 3
        #self.maxval = np.array([9250.875, 18904.68, 25489.98, 22344.435, 22515.21, 29752.92, 2401.56, 16939.53])
        #self.minval = np.array([6354.675, 14136.93, 23362.29, 19848.465, 20443.905, 26452.215, 73.98, 14075.145])

        self.publisher_ = self.create_publisher(Int8, 'mindrove/gesture', 10)


    def listener_callback(self, msg):
        
        #max and min values
        maxv = np.array(msg.max)
        maxval = np.abs(maxv) * 0.045
        minv = np.array(msg.min)
        minval = np.abs(minv) * 0.045
       
        maxval= np.maximum(maxval, minval)
        minval= np.minimum(maxval, minval)

        #this used whenusing datasets for subject 3
        maxval = np.array([9250.875, 18904.68, 25489.98, 22344.435, 22515.21, 29752.92, 2401.56, 16939.53])
        minval = np.array([6354.675, 14136.93, 23362.29, 19848.465, 20443.905, 26452.215, 73.98, 14075.145])

        # ARRAY ADAPTATION (RECTIFICATION)
        np_data = np.array(msg.data)
        emgval = np.abs(np_data) * 0.045
        
        #NORMALIZATION single array 
        normalized_data = np.empty_like(emgval)
        for i in range(emgval.shape[0]):
            normalized_data[i] = ((2 * (emgval[i] - minval[i]) / (maxval[i] - minval[i])) - 1)
        
        #Create QUEUE
        self.data_queue.append(normalized_data.tolist())
        #print("this is normal")
        #print(self.data_queue)
        # MAV
        normal = np.array(self.data_queue)
        pd_normal = pd.DataFrame(normal)
        mav =  np.zeros(8)
        for i in range(8):
            mav[i] = mean(pd_normal.iloc[:,i])
        
        #SSI
        squared = np.square(normal)
        #print("this is squared") 
        #print(squared)
        pd_squared = pd.DataFrame(squared)
        ssi =  np.zeros(8)
        for i in range(8):
            ssi[i] = mean(pd_squared.iloc[:,i])
 
        #print("this is mav")
        #print(mav)
        #print("this is ssi")
        #print(ssi)

        #JOIN MAV AND SSI
        #datasvm correspond to X test
        datasvm = np.asarray([np.concatenate([mav, ssi])])
        #pd_datasvm = pd.DataFrame(datasvm)
        
        #APPLY SVM
        numgest = self.reg.predict(datasvm)
        #https://www.analyticsvidhya.com/blog/2023/02/how-to-save-and-load-machine-learning-models-in-python-using-joblib-library/
        
        
        #TAKE OUT GESTURE
        self.get_logger().info(f'Predicted category is: {numgest}')

        if numgest != 0:
            gesture_msg = Int8()
            gesture_msg.data = int(numgest)
            self.publisher_.publish(gesture_msg)
            

        # self.get_logger().info(f'The gesture recognized is:{self.gesture[int(numgest)]}')
        #self.get_logger().info(f"array recieved is: {msg.data}")

def main(args=None):
    rclpy.init(args=args)

    minimal_subscriber = GestureClassifier()

    rclpy.spin(minimal_subscriber)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_subscriber.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()