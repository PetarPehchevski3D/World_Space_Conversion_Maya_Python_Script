import maya.cmds as cmds
import maya.mel as mel
from sys import exit


#VARIABLES FOR USER TO ADJUST
constraintType = "parent"   # "orient" for rotation,  "point" for translation, "parent" for both
bakeInterval = 1   # You can choose to bake on 1s, 2s, 3s, whatever interval you set
smartBake = False    # Choose between True/False, on whether to use the Smart Bake option
smartBakeIntensity = 5    #This is the intensity of the smart bake. Bigger number means less keys but less accurate animation


#FUNCTIONS
def assistMessage(message, time, toExit):
    #POPS UP A MESSAGE ON THE USER'S SCREEN TO INFORM THEM OF SOMETHING
    cmds.inViewMessage(amg=message, pos='midCenter', fade=True, fst=time, ck=True)
    if toExit == True:
        exit()
        
            
def hideAttributes(type, *controls):
#HIDES UNNECESSARY ATTRIBUTES ON THE CONTROLS        
    for item in controls:
        for attr in ["." + type + "X", "." + type + "Y", "." + type + "Z"]:
            cmds.setAttr(item + attr, k=False, cb=False)


def setConstraint(constraintType, parent, child, translateCurves, rotateCurves):
    #CONSTRAINT FUNCTION
    if constraintType == "parent":
        constraint = cmds.parentConstraint(parent, child, skipTranslate = translateCurves, skipRotate = rotateCurves)[0]
    elif constraintType == "orient":
        constraint = cmds.orientConstraint(parent, child, skip = rotateCurves)[0]
    elif constraintType == "point":
        constraint = cmds.pointConstraint(parent, child, skip = translateCurves)[0]
    
    return constraint


def getConstraintAttribute(constraintType):
    #SETS A KEY ON THE START AND END OF THE TIMELINE, SO THAT WE ENSURE THERE'S A BLEND NODE ALL THE TIME. IF THERE'S NO KEY BEFORE ADDING THE SETUP, THE SCRIPT WON'T APPLY A SWITCH ON THE BLEND NODE
    if constraintType == "orient":
        tempAttribute = "rotate"
    elif constraintType == "point":
        tempAttribute = "translate"
    elif constraintType == "parent":
        tempAttribute = ["translate", "rotate"]
    return tempAttribute
        
def getLockedCurves(obj, attribute):
    #GETS A LIST OF THE LOCKED CURVES FOR EITHER TRANSLATE, ROTATE OR SCALE, SO THE CONSTRAINTS KNOW WHICH CURVES TO AVOID
    curves = {".{0}X".format(attribute):"x", ".{0}Y".format(attribute):"y", ".{0}Z".format(attribute):"z"}
    for curve in curves.copy():
        if cmds.getAttr(obj+curve, l=True) == False:
            curves.pop(curve)
    curves = list(curves.values())
    return curves
            
def setup(obj, tempControl, constraintType, timelineStart, timelineEnd, translateCurves, rotateCurves):
    #ADDS A LOCATORS ONTO EVERY SELECTION AND SWITCHES IT TO WORLD SPACE BY REVERSING THE CONSTRAINTS
    cmds.currentTime(timelineStart)
    cmds.matchTransform(tempControl, obj)
    original_RO = cmds.getAttr(obj + ".rotateOrder")  #STORES THE ROTATION ORDER OF THE CURRENT CONTROL, TO BE ASSIGNED TO THE TEMP CONTROLS
    cmds.setAttr(tempControl + ".rotateOrder", original_RO)
    matchScale(obj, tempControl)
    setConstraint(constraintType, obj, tempControl, translateCurves, rotateCurves)
    cmds.select(tempControl)
    cmds.bakeResults(t=(timelineStart, timelineEnd), pok=True, simulation=False, sr = [smartBake,smartBakeIntensity], sampleBy=bakeInterval)
    if smartBake == True:
        cmds.keyTangent(tempControl, e=True, itt="auto", ott="auto", t=(timelineStart, timelineEnd))
    cmds.filterCurve(tempControl + ".translate", tempControl + ".rotate")
    cmds.delete(cmds.listRelatives(type="constraint"))


def createControl(name):
    #CREATES THE SHAPE OF THE CONTROL
    tempControl = cmds.curve(n=name, degree=1, point=[[-1, 0, -0], [1, 0, 0], [0,0,0], [0,0,-1], [0, 0, 1], [0,0,0], [0,-1,0], [0,1,0]])

    cmds.setAttr(tempControl + ".lineWidth", 3)
    cmds.setAttr(tempControl + ".overrideEnabled", 1)
    cmds.setAttr(tempControl + ".overrideColor", 6)
    return tempControl
            
def matchScale(parent, children, scale=True):
    #SCALE UP AN OBJECT TO ANOTHER ONE'S BOUNDING BOX SCALE, INCASE IT'S BEEN FREEZE-TRANSFORMED. THIS WAY THE USER DOESN'T HAVE TO MANUALLY ADJUST THE SIZE
    children = cmds.ls(children, flatten=True)
    parentShapeNode = cmds.listRelatives(parent, shapes=True)[0]
    
    xMin, yMin, zMin, xMax, yMax, zMax = cmds.exactWorldBoundingBox(parentShapeNode)
    parentDistanceX, parentDistanceY, parentDistanceZ = [xMax-xMin, yMax-yMin, zMax-zMin]
        
    #result=[]
    for child in children:
        xMin, yMin, zMin, xMax, yMax, zMax = cmds.exactWorldBoundingBox(child)
        childDistanceX, childDistanceY, childDistanceZ = [xMax-xMin, yMax-yMin, zMax-zMin]
        
        #WE QUERY THE ORIGINAL SCALE OF THE LOCATOR 
        originalX, originalY, originalZ = cmds.xform(child, q=True, s=True, r=True)
        
        
        divisionX, divisionY, divisionZ = [parentDistanceX/childDistanceX, parentDistanceY/childDistanceY, parentDistanceZ/childDistanceZ]
        
        #WE GET THE FINAL SCALE HERE, WE TAKE THE LONGEST NUMBER AND APPLY THAT TO ALL SCALE AXIS
        largestAxis = max([originalX*divisionX, originalY*divisionY, originalZ*divisionZ]) * 2
        newScale = [largestAxis, largestAxis, largestAxis]
        
        #this part is for return the information outside the function
        #[result.append(i) for i in newScale]

        if scale:
            cmds.xform(child, scale=newScale)
        

def add(a,b):
    result = a + b
    return result
def subtract(a,b):
    result = a - b
    return result   
 


def divideInfluence(curve, timelineStart, timelineEnd, operator, value):
    #USUALLY APPLIED ON AN EMPTY SPACE WHERE THE RANGE ISN'T TOUCHING ANY PRE-EXISTING RANGES, SO IT HANDLES BOTH SIDES - THE START AND END
    cmds.setKeyframe(curve, t=(timelineStart, timelineEnd), value=value)    
    cmds.setKeyframe(curve, t=(timelineStart-1, timelineEnd+1), value=operator(value,1))  

def adjustInfluence(curve, frame, offset, operator, value):
    #USUALLY USED WHEN THE RANGE WE'RE APPLYING IS RIGHT NEXT TO THE END OR START OF AN EXISTING RANGE, SO WE MERGE ONE PART, AND ONLY ADD KEYS ON THE OTHER PART. 
    cmds.setKeyframe(curve, t=(frame), value=value)     
    cmds.setKeyframe(curve, t=(frame + offset), value=operator(value,1))  



def applyInfluenceSwitch(curve, selectionShapeNode, timelineStart, timelineEnd, operator, value, storedFrameValue):
    #FUNCTION THAT HANDLES APPLYING A SWITCH ON THE CONSTRAINT INFLUENCE, AS WELL AS THE VISIBILITY   
    
    keyframes = cmds.keyframe(curve, q=True)
    storedFrames = []

    #WE CHECK TO SEE WHAT EXISTING KEYFRAMES HAVE THE VALUE OF 0 OR 1 (DEPENDING ON IF YOU'VE CHOSEN THE VISIBILITY OR BLEND INDEX CURVES), AND STORE THEM IN A LIST SO THAT WE CAN PAIR THEM UP IN A DICTIONARY
    if keyframes != None:
        for keyframe in keyframes:
            if cmds.keyframe(curve, q=True, t=(keyframe, keyframe), eval=True)[0] == storedFrameValue:
                storedFrames.append(keyframe)
            
    pairedFrames = {storedFrames[frame]: storedFrames[frame + 1] for frame in range(0, len(storedFrames), 2)}
    timelineRange = []
    
    #IF THE TIMELINE RANGE IS IN-BETWEEN 1 OR 2 PAIRS, WE STORE THE START OR THE END OF THE TIMELINE RANGE IN A LIST FOR LATER COMPARISON 
    for start,end in pairedFrames.items():        
        if start - 1 <= timelineStart <= end + 1:
            timelineRange.append(timelineStart)
            
        if start - 1 <= timelineEnd <= end + 1: 
            timelineRange.append(timelineEnd)
        
    
    for start,end in pairedFrames.items():
        #IF OUR TIMELINE RANGE OVERSHADOWS A GIVEN PAIRING OR IS IN-BETWEEN IT, THE SCRIPT WILL ABORT AND THE LOCATOR WON'T BE ADDED
        if timelineStart <= int(start) and int(end) <= timelineEnd or int(start) <= timelineStart and timelineEnd <= int(end) or timelineStart < int(end) and int(start) < timelineEnd :
            assistMessage("<hl>Error: This locator overlaps with another locator on the timeline. <hl>", 5000, True)
 
    confirmation = []
    #IF TIMELINE RANGE IS 0, THAT MEANS THAT OUR RANGE IS NOT INTERSECING WITH ANY EXISTING PAIRINGS AND CAN BE APPLIED NORMALLY
    if len(timelineRange) == 0:
        confirmation = 1
        divideInfluence(curve, timelineStart, timelineEnd, operator, value)
    
    #IF WE'RE TRYING TO FIT A TIMELINE RANGE INBETWEEN 2 OTHER RANGES, THIS CODE GETS EXECUTED 
    
    elif len(timelineRange) == 2:
        cmds.cutKey(curve, t=(timelineStart, timelineStart - 1))
        cmds.cutKey(curve, t=(timelineEnd, timelineEnd + 1))
        confirmation = 1
    else:
        #IF TIMELINE RANGE IS 1, WE CHECK TO SEE IF OUR TIMELINESTART AND TIMELINEEND ARE TOUCHING THE VALUE STORED IN TIMELINERANGE. IF IT IS TOUCHING, WE MERGE THE POINT THEY TOUCH AND EXTEND UP TOWARDS THE OTHER END
        for start,end in pairedFrames.items():
            if timelineStart == int(end) + 1:
                confirmation = 1
                cmds.cutKey(curve, t=(timelineStart - 1, timelineEnd))
                adjustInfluence(curve, timelineEnd, 1, operator, value )
            elif int(start) - 1 == timelineEnd :
                confirmation = 1
                cmds.cutKey(curve, t=(timelineStart, timelineEnd + 1))
                adjustInfluence(curve, timelineStart, -1, operator, value )
    
    #IF TIMELINE RANGE IS 1 OR 2, BUT IT'S OVERLAPPING RATHER THAN TOUCHING ON ONE OF THE ENDS, WELL THEN WE PROCLAIM THAT THE USER CAN'T APPLY THE SETUP
    if confirmation != 1 and selectionShapeNode == curve:
        assistMessage("<hl>Error: This locator overlaps with another locator on the timeline. <hl>", 5000, True)




aTimeSlider = mel.eval('$tmpVar=$gPlayBackSlider')
timeRange = cmds.timeControl(aTimeSlider, q=True, rangeArray=True)

if 2 < (timeRange[1] - timeRange[0]):
    specificTimelineMode = True
    timelineStart = timeRange[0]
    timelineEnd = timeRange[1]
else:
    specificTimelineMode = False
    #QUERIES THE START AND END FRAME OF THE CURRENT TIMELINE
    timelineStart = cmds.playbackOptions(min=True, q=True)
    timelineEnd = cmds.playbackOptions(max=True, q=True)

#PREVENTS THE USER FROM APPLYING THE SETUP IN A NEGATIVE RANGE TIMELINE
if timelineStart < 0 or timelineEnd <0:
    assistMessage("<hl>Error: You can't apply a locator setup on a negative time-range <hl>", 5000, True)

selection = cmds.ls(sl=True)



#ADVISES THE USER TO SELECT SOMETHING BEFORE RUNNING THIS SCRIPT
if len(selection) == 0:
    assistMessage("<hl>You need to select at least 1 object to turn into world space<hl>", 4000, True)
else:            
    for obj in selection:
        #PREVENTS THE USER FROM APPLYING A LOCATOR SETUP ON TOP OF AN EXISTING LOCATOR
        if "Petar3D" in obj:
            assistMessage("<hl>Error: You can't stack locator setups<hl>", 4000, True)
        
        #CHECKS TO SEE IF THERE'S ALREADY AN ORIENT OR A POINT CONSTRAINT, SO THAT IT DOESN'T TRY TO APPLY A PARENT CONSTRAINT, AND VICE VERSA
        if cmds.listConnections(obj, c=True) != None:
            for item in cmds.ls("*_Petar3D_worldSpaceLocator*", tr=True):
                if obj + "_Petar3D_worldSpaceLocator_point" in item and constraintType == "parent" or obj + "_Petar3D_worldSpaceLocator_orient" in item and constraintType == "parent":
                    assistMessage("<hl>Error: You already have an orient/point point constraint applied, you can't apply a parent constraint <hl>", 5000, True)
                if obj + "_Petar3D_worldSpaceLocator_parent" in item and constraintType == "orient" or obj + "_Petar3D_worldSpaceLocator_parent" in item and constraintType == "point":
                    assistMessage("<hl>Error: You already have a parent cosntraint applied, you can't applied an orient/point constraint <hl>", 5000, True)


        #CHECKS TO SEE IF THERE'S ALREADY A NIS-TYPE OF LOCATOR SETUO, AND IF SO IT DOESN'T LET THE USER APPLY AN IFS-TYPE LOCATOR, AND VICE VERSA
        for item in cmds.ls(obj + "_Petar3D*", tr=True):
            if "NIS" in item and specificTimelineMode == True:
                assistMessage("<hl>Error: You already have a locator with overall influence over this selection. You can't mix overall with partial influence locators<hl>", 4000, True)
            elif "IFS" in item and specificTimelineMode == False:
                assistMessage("<hl>Error: You already have a locator with partial influence over this selection. You can't mix partial with overall influence locators<hl>", 4000, True)
        
        #GETS A LIST OF ALL THE LOCKED CURVES SO THAT THE CONSTRAINTS KNOW WHICH CURVES TO SKIP OVER
        translateCurves = getLockedCurves(obj, "translate")       
        rotateCurves = getLockedCurves(obj, "rotate")
        
        #WE CHECK TO SEE IF ALL ROTATE AND TRANSLATE CHANNELS ARE LOCKED. IF THEY ARE, THERE'S NO POINT IN APPLYING THIS SCRIPT
        if len(translateCurves + rotateCurves) != 6:  
            
            #SWITCHES THE VISIBILITY ON THE ORIGINAL SELECTION,
            selectionShapeNode = cmds.listRelatives(obj, shapes=True, children=True)[0]     
            if specificTimelineMode:
                applyInfluenceSwitch(selectionShapeNode + ".v", selectionShapeNode + ".v",  timelineStart, timelineEnd, add, 0, 0)
            else:
                cmds.setAttr(selectionShapeNode + ".v", 0)
            
             #CREATES THE TEMP LOCATOR 
            if specificTimelineMode:
                tempControl = createControl(obj + "_Petar3D_worldSpaceLocator_{0}_IFS_{1}_{2}".format(constraintType, int(timelineStart), int(timelineEnd)))   
            else:
                tempControl = createControl(obj + "_Petar3D_worldSpaceLocator_{0}_NIS".format(constraintType))   
         
            #POSITIONS THE LOCATOR TO THE ORIGINAL SELECTION AND BAKES IT DOWN
            setup(obj, tempControl, constraintType, timelineStart, timelineEnd, translateCurves, rotateCurves)       
            locatorShapeNode = cmds.listRelatives(tempControl, shapes=True, children=True)[0]   
            
            hideAttributes("scale", tempControl)
            cmds.lockNode(tempControl, l=True)
            
            #VISIBILITY SWITCH FOR LOCATOR
            if specificTimelineMode:
                applyInfluenceSwitch(locatorShapeNode + ".v", selectionShapeNode + ".v", timelineStart, timelineEnd, subtract, 1, 0)
        
            
            #CHECKS WHICH ATTRIBUTE TO PLACE THE INITIAL KEYS ON
            tempAttribute = getConstraintAttribute(constraintType)
            
            #CHECKS TO SEE IF THE ORIGINAL CONTROL HAS ANY KEYS ON ITS CURVES ALREADY, AND IF NOT IT PLACES THEM TO ACTIVATE THE BLEND INDEX
            if cmds.keyframe(selection, at =tempAttribute, q=True) == None:
                cmds.setKeyframe(obj, t=(timelineStart, timelineEnd), at=tempAttribute)   
            else:
                cmds.setKeyframe(obj, t=(timelineStart, timelineEnd), at=tempAttribute, pcs=True, i=True)           
            
                            
            #LOCATOR CONSTRAINT SECTION 
            constraint = setConstraint(constraintType, tempControl, obj, translateCurves, rotateCurves)
            #IF THE CONSTRAINT TYPE IS ORIENT, WE APPLY A REVERSE POINT CONSTRAINT
            if constraintType == "orient":
                pointConstraint = setConstraint("point", obj, tempControl, translateCurves, rotateCurves) 
            
            #IF THE RIG IS REFERENCED, WE STORE THE NAME OF THE TEMP LOCATOR WITHOUT THE NAMESPACE, BECAUSE THE COSNTRAINT WE'LL INFLUENCE DON'T HAVE THE NAMESPACE INSIDE
            if cmds.referenceQuery(obj, isNodeReferenced=True) or ":" in obj:                                  
                tempControl = tempControl.split(":")[1]
            
            #WE'RE TRYING TO FIND THE INDEX AT THE END OF THE CONSTRAINT'S WEIGHT ATTRIBUTE. BECAUSE THERE COULD BE MANY CONSTRAINTS APPLIED ON THE SAME OBJECT, WE CAN'T ALWAYS KNOW WHAT THAT NUMBER WILL BE
            for item in cmds.listConnections(constraint, c=True):       
                if "{0}.{1}W".format(constraint, tempControl) in item:
                    constraintIndex = item[-1:]
                 
            #THE CONSTRAINT HAVE A NUMBER AT THE END, WE STORE THIS NUMBER IN A VARIABLE SO WE KNOW WHICH NUMBER TO ATTACHA WHEN WE INFLUENCE THE BLEND NODE
            if specificTimelineMode:
                applyInfluenceSwitch("{0}.{1}W{2}".format(constraint, tempControl, constraintIndex), selectionShapeNode + ".v", timelineStart, timelineEnd, subtract, 1, 0)             
            blendIndex = constraint[-1:]                                           
            
            #BLEND NODE SWITCH SECTION      
            if specificTimelineMode:
                applyInfluenceSwitch("{0}.blend{1}{2}".format(obj, constraintType.capitalize(), blendIndex), selectionShapeNode + ".v", timelineStart, timelineEnd, subtract, 1, 1)
        
        #GIVES THIS ERROR IF ALL 6 CURVES ARE LOCKED AND THERE'S NO POINT IN APPLYING THE SCRIPT
        else:
            assistMessage("<hl>Error: All translate and rotate curves on this selection are locked -  {0} <hl>".format(obj), 4000, False)
    