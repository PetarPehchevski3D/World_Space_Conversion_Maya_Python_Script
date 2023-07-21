"""
This script is part of my space-switching series, inspired by Richard Lico's animation sherpa course, where he goes over the space-switching approach to animating - https://www.animationsherpa.com/
You can use this script for any commercial or non-commercial projects. You're not allowed to sell this script. 
Author - Petar3D
Initial Release Date - 18.07.2023
Version - 1.0

Description - Tool that allows you to apply a temporary locator setup on top of any selection, and it turns it into world-space. The perk of this tool is that you can apply it on a specific range in the timeline, and it 
preserves the original control's animation data.
"""


import maya.cmds as cmds
import maya.mel as mel
from sys import exit

cmds.cycleCheck(e=False)

def formLayout(name, topCoordinates, leftCoordinates):
    #ADJUSTS THE POSITION OF THE UI FEATURES
    cmds.formLayout("formLayout", edit=True, attachForm=[(name, "top",topCoordinates), (name, "left",leftCoordinates)])    

#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#FUNCTIONS
def assistMessage(message, time, toExit):
    #POPS UP A MESSAGE ON THE USER'S SCREEN TO INFORM THEM OF SOMETHING
    cmds.inViewMessage(amg=message, pos='midCenter', fade=True, fst=time, ck=True)
    if toExit == True:
        exit()
        
def documentation():
    cmds.showHelp("https://petarpehchevski3d.gumroad.com/l/worldspaceconversion", a=True)
            
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



#CHECKS FOR WHAT TYPE OF CONSTRAINT DID THE SELECTED CONTROL APPLY ON THE ORIGINAL CONTROL. THEN WE STORE THE TYPE IN VARIABLE, AS WELL AS THE BLEND INDEX
def getBlendIndex(object, blendIndexControl, constraintType):
    for item in cmds.listConnections(object, c=True, type="constraint"):  
        if blendIndexControl + "_" + constraintType + "Constraint" in item:
            tempBlendIndex = item[-1:]
                
            return tempBlendIndex
            

def getConstraintAttribute(constraintType):
    #SETS A KEY ON THE START AND END OF THE TIMELINE, SO THAT WE ENSURE THERE'S A BLEND NODE ALL THE TIME. IF THERE'S NO KEY BEFORE ADDING THE SETUP, THE SCRIPT WON'T APPLY A SWITCH ON THE BLEND NODE
    tempAttribute = []
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
    bakeInterval = cmds.intFieldGrp("BakeInterval_IntField", q=True, v1=True)
    smartBake = cmds.checkBoxGrp("SmartBake_CheckBox", q=True, v1=True)
    smartBakeIntensity = cmds.floatFieldGrp("Intensity_FloatField", q=True, v1=True)
    
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
    

def pseudoSmartBake(originalControl, bakeAttribute, timelineStart, timelineEnd):
    attributes = []
    if len(bakeAttribute) == 2:
        for curve in ["X", "Y", "Z"]:
            for attr in bakeAttribute:
                attributes.append(attr + curve)    
    else:
        for curve in ["X", "Y", "Z"]:
            attributes.append(bakeAttribute + curve)
            
    attributesKeyframes = {}
    for attr in attributes:
        attributesKeyframes[attr] = cmds.keyframe(originalControl, t=(timelineStart,timelineEnd), q=True, at=attr)

    cmds.undo()
    cmds.undo()
    cmds.select(originalControl)
    cmds.bakeResults(originalControl, t = (timelineStart, timelineEnd), pok=True)

    frameRange = []
    #CREATES A LIST OF THE TIMELINE RANGE
    for i in range(int(timelineStart),int(timelineEnd)):
        frameRange.append(i)
    
    #WE GET THE LIST AND REMOVE WHATEVER KEY NEEDS TO BE REMOVED
    for attr,frames in attributesKeyframes.items():
        if frames != None:
            for frame in frames:
                if frame in frameRange:
                    tempRange = frameRange.remove(frame)
            
            for i in frameRange:
                cmds.cutKey(originalControl + "." + attr, t=(i, i))
                

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
 
def getPairedFrames(checkPointOrient, keyword, blendCurve, constraint, timelineStart, timelineEnd):
    #TAKES ALL THE TEMP LOCATORS IN THE SCENE THAT SHARE THE SAME ORIGINAL CONTROL
    pairedFrames = []
    for item in cmds.ls(tr=True):
        if keyword in item:
            if "pointConstraint" not in item:
                #CHECKS TO SEE IF THE ITEMS WE'RE LISTING THROUGH SHARE THE SAME CONSTRAINT TYPE AS OUR CURRENT LOCATOR. IF THEY DO WE ADD THEM TO THE LIST, BECAUSE THOSE ARE THE RELEVANT TIME PAIRINGS WE WANT TO COMPARE AGAINST LATER ON 
                if checkPointOrient:
                    for obj in cmds.listConnections(item):
                        if blendCurve[-1] == obj[-1]:
                            #GETS A LIST OF ALL THE START/END KEYFRAMES FROM THE TEMP CONTROLS THAT SHARE THE SAME ORIGINAL CONTROL BUT EXCLUDES THE CURRENT TEMP LOCATOR FROM THE LIST
                            if str(timelineStart) and str(timelineEnd) not in item:
                                pairedFrames.append(item.split("_")[-2:-1][0])
                                pairedFrames.append(item.split("_")[-1:][0])
                            
                #WE SPLIT IT OFF HERE BECAUSE THIS SECTION IS ONLY FOR VISIBILITY, AND IT NEEDS TO SOURCE FRAMES FROM ALL THE LOCATORS THE SHARE THE SAME ORIGIN, NOT JUST ONES WITH A SPECIFIC CONSTRAINT
                else:
                    if str(timelineStart) and str(timelineEnd) not in item:
                        pairedFrames.append(item.split("_")[-2:-1][0])
                        pairedFrames.append(item.split("_")[-1:][0])
    #WE TAKE THE LIST OF KEYFRAMES AND PAIR THEM UP IN A DICTIONARY SO THAT THEY'RE PROPERLY ARRANGED - START: END
    if len(pairedFrames) != 0:
        pairedFrames = {pairedFrames[frame]: pairedFrames[frame + 1] for frame in range(0, len(pairedFrames), 2)}
        return pairedFrames   



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




def removeInfluence(curve, timelineStart, timelineEnd, dictionary, typeOfCurve):
    #DELETES THE KEYFRAMES AT THE POINT WHERE THE INFLUENCE/VISIBILTIY SWITCHES AND REARRANGES THE KEYS
    tempList = []
    
    #THIS PORTION CHECKS EACH PAIRING FROM THE LIST, AND CHECKS HOW MANY OF THEM MATCH UP WITH OUR TIMELINE'S START AND END, IN OTHER WORDS HOW MANY OF THEM ARE TOUCHING
    if dictionary != None:
        for start,end in dictionary.items():
            if timelineStart == int(end) + 1:
                tempList.append(end)
            elif timelineEnd == int(start) - 1:
                tempList.append(start)
    
    #print(tempList)
    #IF THE LIST IS 0, MEANING THERE'S NO MATCHES, OUR TIMELINE RANGE IS STANDALONE SO WE SIMPLY JUST HAVE TO DELETE THE BEGINNING AND END, NO NEED TO REARRANGE 
    if len(tempList) == 0:
        #print("This locator is isolated")
        cmds.cutKey(curve, t=(timelineStart, timelineEnd))
        cmds.cutKey(curve, t=(timelineStart - 1, timelineEnd + 1))
        #IF THE CURVE IS THE VISIBILITY CURVE, AFTER DELETING THE KEYS WE SET THE VISIBILITY BACK TO 1
        if typeOfCurve == "visibility":
            cmds.setAttr(curve, 1)   
    else:    
        #IF THE LIST IS 2, THAT MEANS THAT BOTH THE TIMELINESTART AND END ARE OVERLAPPING WITH THE START AND END OF OTHER PAIRINGS. IT MEANS OUR RANGE IS STUCK IN THE MIDDLE OF 2 LOCATORS
        if len(tempList) == 2:
            #print("Both timelineStart and timelineEnd are in-between")
            cmds.cutKey(curve, t=(timelineStart, timelineEnd))
            cmds.cutKey(curve, t=(timelineStart - 1, timelineEnd + 1))
            if typeOfCurve == "blend":
                adjustInfluence(curve, timelineStart - 1, 1, subtract, 1 )
                adjustInfluence(curve, timelineEnd, 1, add, 0 )
            else:
                adjustInfluence(curve, timelineStart - 1, 1, add, 0 )
                adjustInfluence(curve, timelineEnd, 1, subtract, 1 )
        
        else:
            if timelineStart == int(tempList[0]) + 1:
                #print("timelineStart is in between")
                #print("eee")
                cmds.cutKey(curve, t=(timelineEnd, timelineEnd + 1))
                if typeOfCurve == "blend":
                    #print("EEEGSAFJAFJ")
                    adjustInfluence(curve, int(tempList[0]), 1, subtract, 1 )
                else:
                    adjustInfluence(curve, int(tempList[0]), 1, add, 0 )
                
            
            elif timelineEnd == int(tempList[0]) - 1:
                #print("timelineEnd is in between")
                cmds.cutKey(curve, t=(timelineStart, timelineStart - 1))
                if typeOfCurve == "blend":
                    adjustInfluence(curve, int(tempList[0]), -1, subtract, 1 )
                else:
                    adjustInfluence(curve, int(tempList[0]), -1, add, 0 )    
    

#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def storeParentConstraint():
    constraintType = "parent"
    worldSpaceConversion(constraintType)

def storeOrientConstraint():
    constraintType = "orient"
    worldSpaceConversion(constraintType)

def storePointConstraint():
    constraintType = "point"
    worldSpaceConversion(constraintType)
    
#EXECUTION
def worldSpaceConversion(constraintType):    
    #VARIABLES FOR USER TO ADJUST
    aTimeSlider = mel.eval('$tmpVar=$gPlayBackSlider')
    timeRange = cmds.timeControl(aTimeSlider, q=True, rangeArray=True)

    if 2 < (timeRange[1] - timeRange[0]):
        specificTimelineMode = True
        timelineStart = timeRange[0]
        timelineEnd = timeRange[1] - 1
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
                    print(item)
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
                    cmds.setKeyframe(obj, t=(timelineStart, timelineEnd), at=tempAttribute, i=True)         
                    
                                
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
        
        

#DELETE SETUP
def deleteSetup():
    selection = cmds.ls(sl=True)
    if len(selection) == 0:
        #NOTIFIES THE USER THAT THEY NEED TO SELECT SOMETHING TO DELETE
        assistMessage("<hl>Error: Nothing is selected<hl>", 4000, False)
        
    bakeInterval = cmds.intFieldGrp("BakeInterval_IntField", q=True, v1=True)
    smartBake = cmds.checkBoxGrp("SmartBake_CheckBox", q=True, v1=True)
    smartBakeIntensity = cmds.floatFieldGrp("Intensity_FloatField", q=True, v1=True)
    

    for temp_locator in selection:
        #WS SETUP
        if "Petar3D_worldSpaceLocator" in temp_locator:
            originalControl = temp_locator.split("_Petar3D_")[:1][0]
            selectionShapeNode = cmds.listRelatives(originalControl, shapes=True, children=True)[0]    #VISIBILITY SWITCH FOR THE ORIGINAL SELECTION
            if "IFS" in temp_locator:
                constraint = temp_locator.split("_")[-4:-3][0]
            elif "NIS" in temp_locator:
                constraint = temp_locator.split("_")[-2:-1][0]
            #IF THE RIG IS REFERENCED, WE STORE THE NAME OF THE TEMP LOCATOR WITHOUT THE NAMESPACE, BECAUSE THE COSNTRAINT WE'LL INFLUENCE DON'T HAVE THE NAMESPACE INSIDE
            if cmds.referenceQuery(originalControl, isNodeReferenced=True) or ":" in originalControl:                                  
                blendIndexControl = originalControl.split(":")[1]
            else:
                blendIndexControl = originalControl
            blendIndex = getBlendIndex(temp_locator, blendIndexControl, constraint)
            blendCurve = originalControl + ".blend{0}{1}".format(constraint.capitalize(), blendIndex)
            
            
            cmds.lockNode(temp_locator, l=False)

            #CHECKS TO SEE IF THE KEYWORD EXISTS IN THE SELECTION, THIS BEING THAT THE LOCATOR AFFECTED A SPECIFIC RANGE OF THE TIMELINE. 
            if "IFS" in temp_locator:
                #EXTRACTS THE INFO FROM THE NAMES
                timelineEnd = int(temp_locator.split("_")[-1:][0])
                timelineStart = int(temp_locator.split("_")[-2:-1][0])
        
                pairedFrames = getPairedFrames(False, originalControl + "_Petar3D", blendCurve, constraint, timelineStart, timelineEnd)
                removeInfluence(selectionShapeNode + ".v", timelineStart, timelineEnd, pairedFrames, "visibility")
            
            #IF THIS ORIGINAL CONTROL DIDN'T HAVE A SPECIFIC INFLUENCE APPLIED, WE JUST REVERT BACK THE VISIBILITY TO THE ORIGINAL AND QUERY THE CURRENT TIMELINE START AND END 
            if "NIS" in temp_locator:
                cmds.setAttr(selectionShapeNode + ".v", 1)
                #QUERIES THE START AND END FRAME OF THE CURRENT TIMELINE
                timelineStart = cmds.playbackOptions(min=True, q=True)
                timelineEnd = cmds.playbackOptions(max=True, q=True)
                
                
            #GETS THE ATTRIBUTE TO BAKE ONTO
            bakeAttribute = getConstraintAttribute(constraint)     
        
            #BAKING THE CURVES
            cmds.currentTime(timelineStart)
            cmds.select(originalControl)
            if smartBake == True:
                cmds.bakeResults(originalControl, t = (timelineStart, timelineEnd), at=bakeAttribute, pok=True, sr=[True, smartBakeIntensity], simulation=False)
                pseudoSmartBake(originalControl, bakeAttribute, timelineStart, timelineEnd)
                
                cmds.keyTangent(e=True, itt="auto", ott="auto", time=(timelineStart, timelineEnd))
                
            else:
                cmds.bakeResults(originalControl, t = (timelineStart, timelineEnd), at=bakeAttribute, sampleBy = bakeInterval, pok=True,simulation=False)
                
        
         
            #REMOVES THE INFLUENCE ON THE BLEND INDEX CURVE        
            if "IFS" in temp_locator:
                pairedFrames = getPairedFrames(True, originalControl + "_Petar3D", blendCurve, constraint + blendIndex, timelineStart, timelineEnd)
                removeInfluence(blendCurve, timelineStart, timelineEnd, pairedFrames, "blend")   
            
        
            #EULER FILTER
            cmds.filterCurve(originalControl + ".translate", originalControl + ".rotate")
            
            #THIS SECTION MAKES SURE THE NEWLY ADJUSTED CURVES ARE FLAT
            if "IFS" in temp_locator:
                #MAKING SURE THAT THE TANGENTS THAT ARE FLAT AT THE END OF IT ALL
                cmds.keyTangent(selectionShapeNode, attribute = "visibility", inTangentType= "flat")
                cmds.keyTangent(originalControl, attribute = "blend{0}{1}".format(constraint.capitalize(), blendIndex), inTangentType= "flat")
            
            cmds.delete(temp_locator)
            
        else:
            #IF AN OBJECT FROM OUTSIDE THE PETAR3D SS SCRIPTS IS SELECTED, IT WON'T COUNT, AND THE USER WILL BE NOTIFIED WHICH OBJECT THEY MISSELECTED
            assistMessage("<hl>Error: Can't run script on this object, it's not a locator set-up  - {0} <hl>".format(temp_locator), 4000, False)
            
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#UI LOGIC
def userInterface():
    if cmds.window("World_Space_Conversion", ex=True):
        cmds.deleteUI("World_Space_Conversion")
    
    cmds.window("World_Space_Conversion", title="World-Space Conversion, by Petar3D", wh=[373, 211], s=False)
    cmds.formLayout("formLayout", numberOfDivisions=100, w=373, h=211)

    cmds.button("Parent_Constraint_Button", l="Parent Constraint", recomputeSize = True, bgc=[0.6220035095750363, 0.9418478675516899, 1.0], h = 50, w = 116,  c="storeParentConstraint()", parent ="formLayout")
    formLayout("Parent_Constraint_Button", 15, 16)

    cmds.button("Orient_Constraint_Button", l="Orient Constraint", recomputeSize = True, bgc=[0.6220035095750363, 1.0, 0.6220035095750363], h = 50.404921049703624, w = 116, c="storeOrientConstraint()", parent ="formLayout")
    formLayout("Orient_Constraint_Button", 79, 16 )
    
    cmds.button("Point_Constraint_Button", l="Point Constraint", recomputeSize = True, bgc=[1.0, 1.0, 0.6220035095750363], h = 50, w = 116, c="storePointConstraint()",  parent ="formLayout")
    formLayout("Point_Constraint_Button", 146, 16)
    
    cmds.button("Delete_Setup_Button", l="Delete Setup", recomputeSize = True, bgc=[1.0, 0.6220035095750363, 0.6220035095750363], h = 50, w = 197, c="deleteSetup()",  parent ="formLayout")
    formLayout("Delete_Setup_Button", 16,154)
    
    cmds.button("Documentation", l="Documentation", recomputeSize = True, bgc=[0.8, 0.8, 0.8], h = 30, w = 100, c="documentation()",  parent ="formLayout")
    formLayout("Documentation", 172,263)

    cmds.intFieldGrp("BakeInterval_IntField", l="Bake Interval: ", numberOfFields=1, v1=1, cw = (1, 90.0), w = 198, parent ="formLayout")
    formLayout("BakeInterval_IntField", 80, 134)
    
    cmds.checkBoxGrp("SmartBake_CheckBox", l="Smart Bake: ", ncb=1, l1="", cw = (1, 72), w = 92, vr=False, v1=False,  parent ="formLayout")
    formLayout("SmartBake_CheckBox", 110,143)
    
    cmds.floatFieldGrp("Intensity_FloatField", l="Intensity", numberOfFields=1, v1=5.0,  cw = (1, 44), w = 128, parent ="formLayout")
    formLayout("Intensity_FloatField", 106, 237)

    cmds.showWindow("World_Space_Conversion")
     
userInterface()