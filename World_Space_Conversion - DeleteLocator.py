import maya.cmds as cmds
from sys import exit


#VARIABLES FOR USER TO ADJUST
bakeInterval = 1   # You can choose to bake on 1s, 2s, 3s, whatever interval you set
smartBake = False   # Choose between True/False, on whether to use the Smart Bake option
smartBakeIntensity = 5    #This is the intensity of the smart bake. Bigger number means less keys but less accurate animation


#FUNCTIONS
def assistMessage(message, time, toExit):
    #POPS UP A MESSAGE ON THE USER'S SCREEN TO INFORM THEM OF SOMETHING
    cmds.inViewMessage(amg=message, pos='midCenter', fade=True, fst=time, ck=True)
    if toExit == True:
        exit()

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
        
def pseudoSmartBake(originalControl, bakeAttribute, timelineStart, timelineEnd):
    attributes = []
    if len(bakeAttribute) == 2:
        for curve in ["X", "Y", "Z"]:
            for attr in bakeAttribute:
                attributes.append(attr + curve)    
    else:
        for curve in ["X", "Y", "Z"]:
            attributes.append(bakeAttribute + curve)
            
    #print(attributes)        
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

def adjustInfluence(curve, frame, offset, operator, value):
    #USUALLY USED WHEN THE RANGE WE'RE APPLYING IS RIGHT NEXT TO THE END OR START OF AN EXISTING RANGE, SO WE MERGE ONE PART, AND ONLY ADD KEYS ON THE OTHER PART. 
    cmds.setKeyframe(curve, t=(frame), value=value)     
    cmds.setKeyframe(curve, t=(frame + offset), value=operator(value,1))  


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
    

#DELETE SETUP
selection = cmds.ls(sl=True)
if len(selection) == 0:
    #NOTIFIES THE USER THAT THEY NEED TO SELECT SOMETHING TO DELETE
    assistMessage("<hl>Error: Nothing is selected <hl>", 4000, False)
    
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
        assistMessage("<hl>Error: Can't run script. This object is not a locator set-up  - {0} <hl>".format(temp_locator), 4000, False)