#!/usr/bin/env python3.8
# -*- coding: utf-8 -*-
"""
Created on Wed May 13 11:45:44 2020

@author: Carlos Gomez-Huelamo

Code to 

Communications are based on ROS (Robot Operating Sytem)

Inputs: 

Outputs:  

Note that 

"""

import math
import numpy as np
import cv2
from shapely.geometry import Polygon

# ROS imports

import rospy
import tf 
import nav_msgs.msg
import visualization_msgs.msg

from t4ac_msgs.msg import Node

# Sklearn imports

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Custom functions 

from aux_functions import geometric_functions
from aux_functions import sort_functions

# Global variables

monitorized_area_gap = 1.8

# Inside Lane functions #

def calculate_aux_point(point,m,delta):
    aux_point = Node()

    if (m == 9999):
        aux_point.x = point.x
        aux_point.y = point.y + delta
    else:
        aux_point.x = point.x + delta
        aux_point.y = m*delta + point.y
    return aux_point

def inside_polygon(p, polygon):
    """
    This functions checks if a point is inside a certain lane (or area), a.k.a. polygon.
    (https://jsbsan.blogspot.com/2011/01/saber-si-un-punto-esta-dentro-o-fuera.html)

    Takes a point and a polygon and returns if it is inside (1) or outside(0).
    """
    counter = 0
    xinters = 0
    detection = False

    p1 = Node()
    p2 = Node()

    p1 = polygon[0] # First column = x coordinate. Second column = y coordinate

    for i in range(1,len(polygon)+1):
        p2 = polygon[i%len(polygon)]

        if (p.y > min(p1.y,p2.y)):
            if (p.y <= max(p1.y,p2.y)):
                if (p.x <= max(p1.x,p2.x)):
                    if (p1.y != p2.y):
                        xinters = (p.y-p1.y)*(p2.x-p1.x)/(p2.y-p1.y)+p1.x
                        if (p1.x == p2.x or p.x <= xinters):
                            counter += 1
        p1 = p2

    if (counter % 2 == 0):
        return False
    else:
        return True

def find_closest_segment(way, point):
    """
    This functions obtains the closest segment (two nodes) of a certain way (left or right)

    Returns the nodes that comprise this segment and the distance
    """

    min_distance = 999999

    closest_node_0 = Node()
    closest_node_1 = Node()

    closest = -1

    for i in range(len(way)-1):
        node_0 = Node()
        node_0.x = way[i].x 
        node_0.y = way[i].y

        node_1 = Node()
        node_1.x = way[i+1].x 
        node_1.y = way[i+1].y

        distance, _ =  geometric_functions.pnt2line(point, node_0, node_1)

        if (distance < min_distance):
            min_distance = distance
            closest = i
            closest_node_0 = node_0
            closest_node_1 = node_1

    if min_distance != 999999:   
        if (closest > 0) and (closest < len(way)-2):
            return closest-1,closest+2,min_distance
        elif (closest > 0) and (closest == len(way)-2):
            return closest-1,closest+1,min_distance
        elif closest == 0 and (len(way) == 2): 
            return 0,1,min_distance
        elif closest == 0 and (len(way) > 2): 
            return 0,2,min_distance
    else:
        return -1, -1, -1

def inside_lane(lane, point,type_object):
    """
    """

    # TODO: Check the left and right ways (they are switched)

    n0l_index, n1l_index, dist2segment_left = find_closest_segment(lane.right.way, point)
    
    if dist2segment_left < 6 and dist2segment_left > 0:
        #print("len: ", len(lane.right.way))
        #print("i0, i1: ", n0l_index, n1l_index)
        n0_left = lane.right.way[n0l_index]
        n1_left = lane.right.way[n1l_index]

        n0_right = lane.left.way[n0l_index]
        n1_right = lane.left.way[n1l_index]
        
        dist2segment_right, _ =  geometric_functions.pnt2line(point, n0_right, n1_right)

        test = lambda dist2segment_left,dist2segment_right : (dist2segment_left,1) if(dist2segment_left <= dist2segment_right) else (dist2segment_right,-1)

        nearest_distance,role = test(dist2segment_left,dist2segment_right)
        lane_width = math.sqrt(pow(n0_right.x-n0_left.x,2)+pow(n0_right.y-n0_left.y,2))

        if type_object == "person" or type_object == "Pedestrian": 
            if (dist2segment_left >= lane_width or dist2segment_right >= lane_width): 
                m = (n0_right.y-n0_left.y) / (n0_right.x-n0_left.x)
                
                # This hypothesis assumes that the obstacle is closer to the left way
                if (round(n0_right.x,2) == round(n0_left.x,2)):
                    m = 9999
                    if (n0_left.y > n0_right.y):
                        delta = monitorized_area_gap
                    else:
                        delta = -monitorized_area_gap 
                elif (n0_left.x > n0_right.x):
                    delta = monitorized_area_gap
                else:
                    delta = -monitorized_area_gap

                delta *= role # If it is closer to the right role, take the opposite

                if role == 1: # Closer to the left way
                    n0_aux = calculate_aux_point(n0_left,m,delta)
                    n1_aux = calculate_aux_point(n1_left,m,delta)
                    polygon = [n0_aux,n1_aux,n1_right,n0_right]
                else:
                    n0_aux = calculate_aux_point(n0_right,m,delta)
                    n1_aux = calculate_aux_point(n1_right,m,delta)
                    polygon = [n0_left,n1_left,n1_aux,n0_aux]
            else: # Inside the original polygon
                polygon = [n0_left,n1_left,n1_right,n0_right]
        else:
            polygon = [n0_left,n1_left,n1_right,n0_right]
        
        road = [n0_left,n1_left,n1_right,n0_right]

        in_polygon = inside_polygon(point, polygon)
        in_road = inside_polygon(point, road)

        
        #print("Is inside polygon: ", in_polygon)
        #print("Is inside road: ", in_road)
        """
        print("Nearest distance: ", nearest_distance)
        print("Point: ", point.x, point.y)
        for pt in polygon:
            print("x y: ", pt.x, pt.y)
        """
        
        return in_polygon, in_road, polygon, nearest_distance
    else:
        return False, False, [], -1

# End Inside Lane functions #

# Monitors functions (ACC, pedestrian crossing, stop, give way) 

   
def calculate_distance_to_nearest_object_inside_route(monitorized_lanes,obstacle_global_position):
    """
    """
    aux_diff = 50000
    accumulated_distance = 0

    for lane in monitorized_lanes.lanes:
        if lane.role == "current" or lane.role == "front":
            x = obstacle_global_position[0]
            y = obstacle_global_position[1]

            for i in range(len(lane.left.way)-1): # Left way (right way could also be used)
                nx = lane.left.way[i].x # Current node
                ny = -lane.left.way[i].y
                #print("current node: ", nx, ny)
                nnx = lane.left.way[i+1].x
                nny = -lane.left.way[i+1].y

                diff = math.sqrt(pow(nx-x,2)+pow(ny-y,2))

                d = math.sqrt(pow(nx-nnx,2)+pow(ny-nny,2))
                #print("d: ", d)
                accumulated_distance += d

                if (diff<aux_diff):
                    aux_diff = diff
                else: # Closest left node to the object
                    return accumulated_distance
            return accumulated_distance # The for has finished, so the object is at the end of the 
                                        # current lane 

# End Monitors functions (predict collision, ACC, pedestrian crossing, stop, give way) 

# Prediction functions #

def predict_collision(predicted_ego_vehicle,predicted_obstacle,static=None,emergency_break=None):
    """
    Search for possible collision between the ego-vehicle and the obstacles predicted positions
    """

    o = 0.0

    if not emergency_break:
        for i,ego in enumerate(predicted_ego_vehicle):
            if static == None: # Dynamic obstacles
                for obs in predicted_obstacle:
                    o = geometric_functions.iou(ego[0],obs) 
                    if o > 0.0: # The predicted position of the ego-vehicle and the predicted position of the obstacle overlap  
                        return int(obs[5]),i # Return the ID of the obstacle and with what ego-vehicle prediction has collided
            else: # Static obstacles
                obs = predicted_obstacle
                o = geometric_functions.iou(ego[0],obs)
                if o > 0.0:  
                    return int(obs[5]),i 
        return -1,-1
    else:
        for i,ego in enumerate(predicted_ego_vehicle):
            obs = predicted_obstacle
            o = geometric_functions.iou(ego[0],obs)
            if o > 0.0:  
                return True 
        return False   

def ego_vehicle_prediction(self, odom_rosmsg, img):
    """ 
    Predict the ego-vehicle trajectory n seconds ahead (in function of its velocity)
    """ 
    LiDAR_centroid_ego = np.array([[self.ego_vehicle_x], [self.ego_vehicle_y], [0.0], [1.0]]) # real-world
    BEV_centroid_ego = np.dot(self.tf_bevtl2bevcenter_m,LiDAR_centroid_ego) # real-world
    BEV_image_centroid_ego = BEV_centroid_ego[:2] # image
    
    BEV_image_centroid_ego[0] = BEV_image_centroid_ego[0]*self.scale_factor[1]
    BEV_image_centroid_ego[1] = BEV_image_centroid_ego[1]*self.scale_factor[0]

    # reference_ego = (int(round(BEV_image_centroid_ego[0].item())), int(round(BEV_image_centroid_ego[1].item())))
    # .item() is used to extract the value in float type, not numpy type
    reference_ego = (int(round(BEV_image_centroid_ego[0])), int(round(BEV_image_centroid_ego[1])))
    cv2.circle(img, reference_ego, radius=4, color=(0,0,255), thickness=4)
    
    self.abs_vel = math.sqrt(pow(odom_rosmsg.twist.twist.linear.x,2)+pow(odom_rosmsg.twist.twist.linear.y,2))

    self.ego_vel_px = -abs(self.abs_vel)*self.scale_factor[0] # m/s to pixels/s
    self.ego_vz_px = -odom_rosmsg.twist.twist.angular.z # No conversion is required (rad/s) # It is the opposite in OpenCV!
    
    message = 'Ego-vehicle velocity (km/h): ' + str(round(self.abs_vel*3.6,2))
    cv2.putText(img,message,(30,110), cv2.FONT_HERSHEY_PLAIN, 1.5, [255,255,255], 2)
    
    ego_dimensions_m = np.array([[4.4],  # Length
                                 [1.8]]) # Width 
    ego_length_px = ego_dimensions_m[0]*self.scale_factor[0]
    ego_width_px = ego_dimensions_m[1]*self.scale_factor[1]
    
    s = ego_length_px*ego_width_px # Area of the bounding box
    r = ego_width_px/ego_length_px # Aspect ratio

    # Predict ego-vehicle trajectory

    self.ego_predicted = []
    vel_km_h = self.abs_vel*3.6 # m/s to km/h

    print("Ego vehicle vel: ", vel_km_h)
    if abs(self.abs_vel) != 0.0: # The vehicle is moving   
        pf = PolynomialFeatures(degree = 2)
        self.ego_braking_distance = self.velocity_braking_distance_model.predict(pf.fit_transform([[vel_km_h]]))
        
        seconds_required = self.ego_braking_distance/self.abs_vel

        if seconds_required < 3:
            seconds_required = 3 # Predict the trajectory at least 3 seconds ahead

        for i in range(self.n.shape[0]):
            self.n[i] = float(seconds_required)/float(self.n.shape[0])*(i+1)
    else:
        self.ego_braking_distance = 0
        self.n = np.zeros((4,1))
    
    # Predict
    
    previous_angle_aux = 0
    
    quaternion = np.zeros((4))
    quaternion[0] = odom_rosmsg.pose.pose.orientation.x
    quaternion[1] = odom_rosmsg.pose.pose.orientation.y
    quaternion[2] = odom_rosmsg.pose.pose.orientation.z
    quaternion[3] = odom_rosmsg.pose.pose.orientation.w

    euler = tf.transformations.euler_from_quaternion(quaternion)
    self.current_yaw = euler[2]

    for i in range(self.n.shape[0]):  
        if i>0:
            previous_angle_aux = self.ego_trajectory_prediction_bb[4,i-1]
        else:               
            if not self.initial_angle:
                self.previous_angle = math.pi/2
                self.initial_angle = True
            else:
                diff = self.current_yaw - self.pre_yaw
                self.ego_orientation_cumulative_diff += diff
                self.previous_angle = self.previous_angle #- diff
                previous_angle_aux = self.previous_angle
                
            self.pre_yaw = self.current_yaw

        self.ego_trajectory_prediction_bb[0,i] = BEV_image_centroid_ego[0] + self.ego_vel_px*self.n[i]*math.cos(previous_angle_aux) # x centroid
        self.ego_trajectory_prediction_bb[1,i] = BEV_image_centroid_ego[1] + self.ego_vel_px*self.n[i]*math.sin(previous_angle_aux) # y centroid
        self.ego_trajectory_prediction_bb[2,i] = s # s (scale) is assumed to be constant for the ego-vehicle
        self.ego_trajectory_prediction_bb[3,i] = r # r (aspect ratio) is assumed to be constant for the ego-vehicle
        self.ego_trajectory_prediction_bb[4,i] = self.previous_angle +  self.ego_vz_px*self.n[i] # Theta (orientation). 
        # Note that the ego-vehicle is initially up-right according to the image
        
        e = sort_functions.convert_x_to_bbox(self.ego_trajectory_prediction_bb[:,i])
        self.ego_predicted.append(e)

    self.angle_bb = self.ego_orientation_cumulative_diff + math.pi/2

    # Visualize

    if self.display:
        for j in range(self.n.shape[0]):           
            e = self.ego_predicted[j][0]
            e1c, e2c, e3c, e4c = geometric_functions.compute_corners(e)
  
            contour = np.array([[e1c[0],e1c[1]],[e2c[0],e2c[1]],[e3c[0],e3c[1]],[e4c[0],e4c[1]]])
            centroid = (e[0].astype(int),e[1].astype(int)) # tracker centroid
            color = (0,0,255)
            my_thickness = 2
            geometric_functions.draw_rotated(contour,centroid,img,my_thickness,color)

# End Prediction functions #

# ROS functions

# TODO: Use custom topic to public additional information?
# TODO: Wireframe (using line_strip) to paint the trajectory prediction
def tracker_to_topic(self,tracker,type_object,color,j=None):
    """
    Fill the obstacle features using real world metrics. Tracker presents a predicted state vector 
    (x,y,w,l,theta) in pixels, in addition to its ID. The x,y,w,l must be trasformed into meters.
    """
    tracked_obstacle = visualization_msgs.msg.Marker()
    
    tracked_obstacle.header.frame_id = "/ego_vehicle/lidar/lidar1"
    tracked_obstacle.header.stamp = rospy.Time.now()
    tracked_obstacle.ns = "tracked_obstacles"
    tracked_obstacle.action = tracked_obstacle.ADD

    if type_object == "Pedestrian": 
        tracked_obstacle.type = tracked_obstacle.CYLINDER
    else:
        tracked_obstacle.type = tracked_obstacle.CUBE
        
    tracked_obstacle.id = tracker[5].astype(int)

    aux_points = np.array([[tracker[0]], [tracker[1]], [0.0], [1.0]]) # Tracker centroid in pixels
    aux_centroid = np.dot(self.tf_bevtl2bevcenter_px,aux_points)
    aux_centroid = np.dot(self.tf_lidar2bev,aux_centroid)

    real_world_x,real_world_y,real_world_w,real_world_l = geometric_functions.compute_corners(tracker,self.shapes,aux_centroid)

    real_world_x = real_world_x[0]
    real_world_y = real_world_y[0]
    real_world_h = 1.7 # TODO: 3D Object Detector information?
    real_world_z = -1.7 # TODO: 3D Object Detector information?
    
    tracked_obstacle.pose.position.x = real_world_x   
    tracked_obstacle.pose.position.y = real_world_y
    tracked_obstacle.pose.position.z = real_world_z
    
    tracked_obstacle.scale.x = 0.7
    tracked_obstacle.scale.y = 0.7
    tracked_obstacle.scale.z = 1.5
    
    quaternion = tf.transformations.quaternion_from_euler(0,0,-tracker[4]) # The orientation is exactly the opposite since
    # we are going to publish this object in ROS (LiDAR frame) but we have tracked it using a KF/HA based on BEV camera perspective
    
    tracked_obstacle.pose.orientation.x = quaternion[0]
    tracked_obstacle.pose.orientation.y = quaternion[1]
    tracked_obstacle.pose.orientation.z = quaternion[2]
    tracked_obstacle.pose.orientation.w = quaternion[3]
    
    if type_object == "trajectory_prediction":
        tracked_obstacle.id = tracker[5].astype(int)*100 + j
        tracked_obstacle.color.a = 0.2
 
    else:
        tracked_obstacle.color.a = 1.0
        
    tracked_obstacle.color.r = color[2]
    tracked_obstacle.color.g = color[1]
    tracked_obstacle.color.b = color[0]

    tracked_obstacle.lifetime = rospy.Duration(1.0) # 1 second

    self.trackers_marker_list.markers.append(tracked_obstacle)
    
    if type_object != "trajectory_prediction":
        ret = [real_world_h,real_world_w,real_world_l,real_world_x,real_world_y,real_world_z,tracker[5].astype(int)]
        return ret
    else:
        return

def empty_trackers_list(self):
    tracker = visualization_msgs.msg.Marker()
                    
    tracker.header.stamp = rospy.Time.now()
    tracker.header.frame_id = "/ego_vehicle/lidar/lidar1"
    tracker.ns = "tracked_obstacles"
    tracker.type = 3
    
    tracker.scale.x = 0.1
    tracker.scale.y = 0.1
    tracker.scale.z = 0.1
    
    self.trackers_marker_list.markers.append(tracker)

# End ROS functions

# Braking distance-Velocity model

def fit_velocity_braking_distance_model():
    """
    This function creates a regression model to determine the braking distance in function of the velocity. It needs
    two arrays to create the model

    Data: https://cdn3.capacitateparaelempleo.org/assets/76k9ldq.pdf
    Theory: http://www.dgt.es/PEVI/documentos/catalogo_recursos/didacticos/did_adultas/velocidad.pdf
    """

    velocity_braking_distance_model = LinearRegression()

    a = np.array((40,50,60,70,80,90,100,110,120,130,140)).reshape(11,1) 
    b = np.array((18.62,26.49,35.65,46.09,57.82,70.83,85.13,100.72,117.59,135.75,155.20)).reshape(11,1)

    pf = PolynomialFeatures(degree = 2)
    a = pf.fit_transform(a.reshape(-1,1)) # The x-axis is transformed to polynomic
    velocity_braking_distance_model.fit(a, b) 

    return velocity_braking_distance_model

# Store Multi-Object Tracking in KITTI format

def store_kitti(num_image,path,object_type,world_features,object_properties):
    # Write the object in KITTI validation format:
    # Number of frame, Object ID, Object type, Truncation, Oclusion, Alpha_angle, Left coordinate, Top coordinate, Right coordinate, 
    # Bottom coordinate, Width, Length, Height, 3D location X, 3D location Y, 3D location Z, Angle, Score

    # We assume 0 truncation, 0 occlusion.

    if (object_type == "person"):
        object_type = "Pedestrian"
    elif (object_type == "car"):
        object_type = "Car"
    elif (object_type == "bicycle"):
        object_type = "Cyclist"

    file = open(path, 'a')

    kitti_x = -world_features[4]
    kitti_y = -world_features[5]
    kitti_z =  world_features[3]

    kitti_data = str(num_image) + ' ' + str(d[5].astype(int)) + ' ' + str(object_type) + ' ' + str(0) + ' ' + str(0) + ' ' + str(object_properties[0]) + ' ' + str(0) + ' ' + str(0) + ' ' + str(0) + ' ' + str(0) + ' ' + str(world_features[0]) + ' ' + str(world_features[1]) + ' ' + str(world_features[2]) + ' ' + str(kitti_x) + ' ' + str(kitti_y) + ' ' + str(kitti_z) + ' ' + str(object_properties[1]) + ' ' + str(object_properties[2])
    # To compare with CARLA groundtruth -> kitti_data = str(self.num_image) + ' ' + str(d[5].astype(int)) + ' ' + str(object_type) + ' ' + str(0) + ' ' + str(0) + ' ' + str(object_observation_angle) + ' ' + str(0) + ' ' + str(0) + ' ' + str(0) + ' ' + str(0) + ' ' + str(world_features[0]) + ' ' + str(world_features[1]) + ' ' + str(world_features[2]) + ' ' + str(kitti_z) + ' ' + str(-kitti_x) + ' ' + str(kitti_y) + ' ' + str(object_rotation) + ' ' + str(object_score)

    file.write(kitti_data + '\n')

    file.close()






 





        


   
    
    
    
        
    
    
