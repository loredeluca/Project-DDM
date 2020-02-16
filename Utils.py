import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
import statistics as stat
import math
import os
import glob
import networkx as nx
from skimage.filters import (threshold_otsu, threshold_sauvola)
from skimage.transform import hough_line
from skimage import measure
from sklearn.preprocessing import binarize
from scipy.sparse.csgraph import minimum_spanning_tree
from sklearn.neighbors import kneighbors_graph
import PreProcessing as pp
import LayoutAnalysis as la

def showImage(text_name, file_name):
    '''
    It shows the image creating a new OpenCV window, it also write the image on a file.
    
    Parameters
    ----------
    text_name : string about the file named used to show and write
    file_name: array of image pixels to show.
    '''
    cv.namedWindow(text_name, cv.WINDOW_NORMAL)
    cv.imshow(text_name, file_name)
    cv.imwrite(text_name+'.tif', file_name)
    #cv.imwrite(text_name, file_name)
    cv.waitKey(0)
    cv.destroyWindow(text_name)
    
def removeFiguresOrSpots(binarized_img, mode):
    '''
    Remove figures or spots from images, useful for making more accurate the deskew with Hough transform.
    
    Parameters
    ----------
    binarized_img : array of binarized image pixels.
    original_img: array of original image pixels.
    mode : string used for selection of mode. 

    Returns
    -------
    new_img : array of original image pixels without figures or spots.
    '''
    new_img = binarized_img.copy()
    if new_img.ndim >2:
        new_img = cv.cvtColor(new_img, cv.COLOR_BGR2GRAY)
    contours,_ = cv.findContours(~binarized_img, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
    
    for contour in contours:
        [x,y,w,h] = cv.boundingRect(contour) #posso usare cv.contourArea(contour)
        if mode == 'figures':
            if w>300 or h>300 :#remove if the box it's too big (figure) or if it's too small (spot)
                for i in range(y,y+h):
                    for j in range(x, x+w):
                        new_img[i][j] = 255
        elif mode == 'spots':
            if ((0<=w<=8) and (0<=h<=8)):  #DACONTROLLARE (RIMUOVE PUNTI)
                for i in range(y,y+h):
                    for j in range(x, x+w):
                        new_img[i][j] = 255
        elif mode == 'linesVert':
            if h>50 and w<20:
                for i in range(y,y+h):
                    for j in range(x, x+w):
                        new_img[i][j] = 255
        elif mode == 'linesHoriz':
            if w>50 and h<20:
                for i in range(y,y+h):
                    for j in range(x, x+w):
                        new_img[i][j] = 255
        elif mode == 'linesBoth':
            if (w>50 and h<20) or (h>50 and w<20):
                for i in range(y,y+h):
                    for j in range(x, x+w):
                        new_img[i][j] = 255
                        
    #showImage('gn',new_img)
    return new_img

def printContours(binarized_img,output_img, thickness):
    '''
    Draw a green rectangle (if the image is not in grayscale) around to characters/words.
    
    Parameters
    ----------
    binarized_img : array of binarized image pixels.
    output_img: array of output image pixels. This will be modified at the end of the method.
    '''
    
    #contours,_  = cv.findContours(np.uint8(np.logical_not(binarized_img)),cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE) 
    contours,_  = cv.findContours(~binarized_img,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE) 
    for contour in contours:
        [x,y,w,h] = cv.boundingRect(contour)
        if w >= 4 and h >= 4:
            cv.rectangle(output_img, (x,y), (x+w,y+h), (0, 255, 0), thickness)
            
            
def findMidDistanceContour(binarized_img,vert: bool = False):
    contours,_  = cv.findContours(~binarized_img,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE) 
    sumDir = 0
    size = 0
    for contour in contours:
        [x,y,w,h] = cv.boundingRect(contour)
        if vert:
            sumDir += h
        else:
            sumDir += w
        size += 1
    midV = sumDir/size
    return midV
    



#trova la distanza tra centroidi
def findDistance(binarized_img, vert: bool = False):
    points = la.findCentroids(binarized_img,binarized_img.copy())
    G,edges = la.minimumSpanningTreeEdges(points,5)
    edges_dist = G.data
    edges_hor,edges_vert = edgesInformation(edges,points,edges_dist)
    distances = []
    edges = edges_hor
    if vert:
        edges = edges_vert
    for edge in edges:
        c1,c2 = edge[2]
        x1,y1 = points[c1]
        x2,y2 = points[c2]
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        distances.append(dist)
       
    #DA VERIFICARE MEGLIO
    for dist in distances:
        if dist > 100:
            distances.remove(dist)
            print('RIMOSSO',dist)
    
    
    return distances


def histogram(binarized_img,distance,vert: bool = False):
    w=findMidDistanceContour(binarized_img,vert)
    row_number = [i for i in range(len(distance))]
    distances=[]
    for j in range(len(distance)):
        distances.append(distance[j]-w)
    plt.bar(row_number,distances)
    plt.show()        
              
    
def rotate(img_orig,img_bin):
    img_copy = img_orig.copy()
    printContours(img_bin,img_copy, 1)       

    valueH,_= pp.valueRLSA(img_bin)
    valueV,_ = pp.valueRLSA(img_bin,True)
    
    img_rlsa_H = pp.rlsa(img_bin.copy(), True, False, valueH)
    img_rlsa_full = pp.rlsa(img_rlsa_H.copy(),False,True,valueV)
    
    img_no_figures = removeFiguresOrSpots(img_rlsa_full, 'figures')
    #showImage('puppu',img_no_figures)
    img_rotated,_ = pp.houghTransformDeskew(img_no_figures, img_orig, False)
    return img_rotated

def showProjection(img_bin, counts, row_number):
    
    f, (ax1,ax2)= plt.subplots(1, 2, sharey=True, figsize=(70, 20))#(70,40)
    ax1.imshow(img_bin,'gray')
    ax1.tick_params(axis='both', which='major', labelsize=30)
    ax2.plot(counts, row_number,label='fit')
    ax2.tick_params(axis='both', which='major', labelsize=30)
    plt.xlabel('Number of Black Pixels',fontsize=40)
    plt.ylabel('Row Number',fontsize=40)
    plt.subplots_adjust( wspace = 0)
    plt.show()
    
    
def rectContains(rect, point) :
    '''
    Calculates the belonging of a point to a given rectangle.
    
    Parameters
    ----------
    rect: tuple that contains origin and size of the image rectangle
    point : coordinate (x, y) of a point
    
    Returns
    -------
    contains: boolean value
    '''
    if point[0] < rect[0] :
        return False
    elif point[1] < rect[1] :
        return False
    elif point[0] > rect[2] :
        return False
    elif point[1] > rect[3] :
        return False
    return True

def euclidean_distance(point1, point2):
	distance = (point2[0] - point1[0])**2 + (point2[1] - point1[1])**2
	return math.sqrt(distance)

def angleBetween(p1, p2):
    dx = p2[1]-p1[1]
    dy = p2[0]-p1[0]
    arctan = math.atan2(dx,dy)
    return math.degrees(arctan)

def getAngles(edges,points):
    angles = []
    for edge in edges:
        #i, j = edge
        i,j = edge
        angles.append(angleBetween(points[i],points[j]))
    return angles

def plotEdges(img, edges, points):
    plt.figure(figsize=(30,20))
    plt.imshow(img, 'gray')  
    for edge in edges:
        #i, j = edge
        i,j = edge
        plt.plot([points[i, 0], points[j, 0]], [points[i, 1], points[j, 1]], c='r')
    plt.show() 
    
def edgesInformation(edges, points, distances):
    angles = getAngles(edges,points)
    

    horizontal_edges =[]
    vertical_edges = []
    munnezza = []
    for i in range(len(angles)):
    
        #if -24< angles[i] < 24 or 156 < angles[i] or angles[i] < -156:
        if -15< angles[i] < 15 or 165 < angles[i] or angles[i] < -165:
            horizontal_edges.append((angles[i],distances[i],[edges[i][0],edges[i][1]]))
        elif 75 < angles[i] < 105 or (-75 > angles[i] and angles[i] > -105)  :
            vertical_edges.append((angles[i],distances[i],[edges[i][0],edges[i][1]]))
        else:
            munnezza.append((angles[i],distances[i],[edges[i][0],edges[i][1]]))
    
    return horizontal_edges,vertical_edges

def polyArea(x,y):
    return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))