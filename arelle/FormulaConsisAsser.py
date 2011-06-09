'''
Created on Jan 9, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle import (XbrlConst)
from arelle.XbrlUtil import (xEqual,S_EQUAL2)
from arelle.ValidateXbrlCalcs import (inferredPrecision, roundValue)
from math import fabs

def evaluate(xpCtx, varSet, derivedFact):
    # there may be multiple consis assertions parenting any formula
    for consisAsserRel in xpCtx.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionFormula).toModelObject(varSet):
        consisAsser = consisAsserRel.fromModelObject
        hasProportionalAcceptanceRadius = consisAsser.hasProportionalAcceptanceRadius
        hasAbsoluteAcceptanceRadius = consisAsser.hasAbsoluteAcceptanceRadius
        if derivedFact is None:
            continue
        isNumeric = derivedFact.isNumeric
        if isNumeric and not derivedFact.isNil:
            derivedFactInferredPrecision = inferredPrecision(derivedFact)
            if derivedFactInferredPrecision == 0 and not hasProportionalAcceptanceRadius and not hasAbsoluteAcceptanceRadius:
                if xpCtx.formulaOptions.traceVariableSetExpressionResult:
                    xpCtx.modelXbrl.error( _("Consistency assertion {0} formula {1} fact {2} has zero precision and no radius is defined, skipping consistency assertion").format(
                         consisAsser.id, varSet.xlinkLabel, derivedFact),
                        "info", "formula:trace")
                continue
    
        # check xbrl validity of new fact
        
        # find source facts which match derived fact
        aspectMatchedInputFacts = []
        isStrict = consisAsser.isStrict
        for inputFact in xpCtx.modelXbrl.facts:
            if (not inputFact.isNil and
                inputFact.qname == derivedFact.qname and
                inputFact.context.isEqualTo(derivedFact.context,
                                            dimensionalAspectModel=(varSet.aspectModel == "dimensional")) and
                (not isNumeric or inputFact.unit.isEqualTo(derivedFact.unit))):
                aspectMatchedInputFacts.append( inputFact )
        
        if len(aspectMatchedInputFacts) == 0:
            if isStrict:
                if derivedFact.isNil:
                    isSatisfied = True
                else:
                    isSatisfied = False
            else:
                if xpCtx.formulaOptions.traceVariableSetExpressionResult:
                    xpCtx.modelXbrl.error( _("Consistency assertion {0} Formula {1} no input facts matched to {2}, skipping consistency assertion").format( 
                        consisAsser.id, varSet.xlinkLabel, derivedFact),
                        "info", "formula:trace")
                continue
        elif derivedFact.isNil:
            isSatisfied = False
        else:
            isSatisfied = True
                
        paramQnamesAdded = []
        for paramRel in consisAsser.orderedVariableRelationships:
            paramQname = paramRel.variableQname
            paramVar = paramRel.toModelObject
            paramValue = xpCtx.inScopeVars.get(paramVar.qname)
            paramAlreadyInVars = paramQname in xpCtx.inScopeVars
            if not paramAlreadyInVars:
                paramQnamesAdded.append(paramQname)
                xpCtx.inScopeVars[paramQname] = paramValue
        for fact in aspectMatchedInputFacts:
            if isSatisfied != True: 
                break
            if fact.isNil:
                if not derivedFact.isNil:
                    isSatisfied = False
            elif isNumeric:
                factInferredPrecision = inferredPrecision(fact)
                if factInferredPrecision == 0 and not hasProportionalAcceptanceRadius and not hasAbsoluteAcceptanceRadius:
                    if xpCtx.formulaOptions.traceVariableSetExpressionResult:
                        xpCtx.modelXbrl.error( _("Consistency assertion {0} Formula {1} input fact matched to {2} has zero precision and no radius, skipping consistency assertion").format( 
                            consisAsser.id, varSet.xlinkLabel, derivedFact),
                            "info", "formula:trace")
                        isSatisfied = None
                        break
                if hasProportionalAcceptanceRadius or hasAbsoluteAcceptanceRadius:
                    acceptance = consisAsser.evalRadius(xpCtx, derivedFact.vEqValue)
                    if acceptance is not None:
                        if hasProportionalAcceptanceRadius:
                            acceptance *= derivedFact.vEqValue
                        isSatisfied = fabs(derivedFact.vEqValue - fact.vEqValue) <= fabs(acceptance)
                    else:
                        isSatisfied = None  # no radius
                else:
                    p = min(derivedFactInferredPrecision, factInferredPrecision)
                    if (p == 0 or
                        roundValue(derivedFact.vEqValue, precision=p) != roundValue(fact.vEqValue, precision=p)):
                        isSatisfied = False
            else:
                if not xEqual(fact.concept, fact.element, derivedFact.element, equalMode=S_EQUAL2):
                    isSatisfied = False
        for paramQname in paramQnamesAdded:
            xpCtx.inScopeVars.pop(paramQname)
        if isSatisfied is None:
            continue    # no evaluation
        if xpCtx.formulaOptions.traceVariableSetExpressionResult:
            xpCtx.modelXbrl.error( _("Consistency Assertion {0} result {1}").format( consisAsser.id, isSatisfied),
                "info", "formula:trace")
        message = consisAsser.message(isSatisfied)
        if message:
            xpCtx.modelXbrl.error(message.evaluate(xpCtx), "info", "message:" + consisAsser.id)
        if isSatisfied: consisAsser.countSatisfied += 1
        else: consisAsser.countNotSatisfied += 1