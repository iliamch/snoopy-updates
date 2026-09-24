"""Authored character phases and visitors over a fixed doghouse.

Only complete actions fit inside a section. Every action follows its start-pose
bridge, intro/loop/outro and end pose; independent visitors keep their plane.
"""
import random
from datetime import datetime,timezone
from .core import matches

def moon_tag(utc=None):
    # Mean synodic month: approximate phase, not an astronomical ephemeris.
    utc=utc or datetime.now(timezone.utc)
    age=(utc-datetime(2000,1,6,18,14,tzinfo=timezone.utc)).total_seconds()/86400
    phase=int((age%29.530588853)/29.530588853*8+.5)%8
    return 'weather:'+('moonNew','moonWaxingCrescent','moonFirstQuarter','moonWaxingGibbous',
                       'moonFull','moonWaningGibbous','moonLastQuarter','moonWaningCrescent')[phase]

def allowed(asset, house, tags, weather, exclusions):
    field={'characterAdditionalPose':'excludedCharacterAdditionalPoses',
           'characterMoment':'excludedCharacterMoments','idleSceneVisitor':'excludedVisitors'}.get(asset['Kind'])
    return (asset['Id'] not in exclusions.get(field,[]) and
            (not asset.get('Parents') or house in asset['Parents']) and
            matches(asset['Rules'],tags,True) and not set(asset['Excluded'])&weather and
            all(set(group)&weather for group in asset['Dependencies']))

def phases(asset, loops):
    result=[]
    for phase in ('oneShot','intro','loop','outro'):
        layers=[l for l in asset['Layers'] if l['Phase']==phase]
        if layers:
            duration=max(l['Duration'] for l in layers)*(loops if phase=='loop' else 1)
            result.append((layers,duration))
    return result

class Program:
    def __init__(self,catalog,selection,tags,duration,rng=None,used=None):
        self.rng=rng or random.Random();self.used=used if used is not None else set()
        self.character=[];self.visitors=[];self.events=[];self.duration=duration
        assets=catalog['Assets'];house=selection['house']['Id'];self.house=house
        weather=set(selection['effect']['Rules'])&set(tags) if selection['effect'] else set()
        weather={t for t in weather if t.startswith('weather:')}
        exclusions=catalog['Houses'].get(house,{})
        eligible=[a for a in assets if allowed(a,house,set(tags),weather,exclusions)]
        actions=[a for a in eligible if a['Kind'] in ('characterAdditionalPose','characterMoment')]
        transitions={(a['Start'],a['End']):a for a in assets if a['Kind']=='characterPoseTransition'}
        poses={p['Id']:p for p in selection['poses']}
        pose='101_BP003' if '101_BP003' in poses else selection['pose']['Id'];t=0.0
        def rest(length):
            nonlocal t
            length=min(length,duration-t)
            self.character.append(dict(Start=t,Duration=length,Asset=poses[pose],Layers=poses[pose]['Layers'],Pose=True))
            t+=length
        # One event lane: visitors and character actions never compete.
        resting=pose
        pool=actions+[a for a in eligible if a['Kind']=='idleSceneVisitor']
        last_kind=None
        rest(self.rng.uniform(18,28))
        while t<duration:
            choices=[]
            for a in pool:
                visitor=a['Kind']=='idleSceneVisitor'
                parts=[]
                if visitor:
                    parts=[(a,l,d) for l,d in phases(a,2)]
                else:
                    bridge=transitions.get((resting,a['Start'])) if resting!=a['Start'] else None
                    back=transitions.get((a['End'],resting)) if a['End']!=resting else None
                    if (resting!=a['Start'] and not bridge) or (a['End']!=resting and not back):continue
                    if bridge:parts.extend((bridge,l,d) for l,d in phases(bridge,1))
                    parts.extend((a,l,d) for l,d in phases(a,2))
                    if back:parts.extend((back,l,d) for l,d in phases(back,1))
                if t+sum(p[2] for p in parts)+10<=duration:choices.append((a,parts,visitor))
            if not choices:rest(duration-t);break
            fresh=[p for p in choices if p[0]['Id'] not in self.used]
            if not fresh:
                self.used.difference_update(a['Id'] for a,_,_ in choices);fresh=choices
            alternate=[p for p in fresh if p[2]!=last_kind]
            action,parts,visitor=self.rng.choice(alternate or fresh)
            self.used.add(action['Id']);last_kind=visitor
            self.events.append(dict(Time=t,Id=action['Id'],Visitor=visitor,From=resting,To=resting))
            if visitor:
                cursor=t
                for asset,layers,length in parts:
                    self.visitors.append(dict(Start=cursor,Duration=length,Asset=asset,Layers=layers,Pose=False));cursor+=length
                rest(cursor-t)
            else:
                for asset,layers,length in parts:
                    self.character.append(dict(Start=t,Duration=length,Asset=asset,Layers=layers,Pose=False));t+=length
            pose=resting
            rest(self.rng.uniform(25,45))

    def at(self,seconds):
        character=next((s for s in self.character if s['Start']<=seconds<s['Start']+s['Duration']),self.character[-1])
        visitors=[s for s in self.visitors if s['Start']<=seconds<s['Start']+s['Duration']]
        return character,visitors
