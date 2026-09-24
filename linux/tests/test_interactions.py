import unittest,random
from snoopy.interactions import Program,allowed,phases

def asset(id,kind='characterMoment',start='a',end='b',rules=None):
    return dict(Id=id,Kind=kind,Start=start,End=end,Rules=rules or [],Excluded=[],Dependencies=[],Parents=[],IgnoreOffset=False,
                Layers=[dict(Phase='oneShot',Duration=2,Files=['test.png'],Fps=1,Loop=False,Plane='foregroundCharacter')])

class InteractionTests(unittest.TestCase):
    def selection(self):
        poses=[dict(Id=p,Layers=[]) for p in ('a','b')]
        return dict(house=dict(Id='house'),pose=poses[0],poses=poses,effect=None)
    def test_no_truncated_actions_and_returns_to_authored_pose(self):
        catalog=dict(Assets=[asset('action'),asset('back','characterPoseTransition','b','a')],Houses={})
        p=Program(catalog,self.selection(),set(),60,random.Random(7))
        self.assertTrue(p.events);self.assertTrue(p.character[-1]['Pose'])
        self.assertAlmostEqual(sum(s['Duration'] for s in p.character),60)
        for before,after in zip(p.character,p.character[1:]):
            self.assertAlmostEqual(before['Start']+before['Duration'],after['Start'])
            if before['Asset']['Id']=='action':self.assertEqual(after['Asset']['Id'],'back')
        self.assertEqual(p.house,'house')
    def test_unknown_transition_does_not_teleport(self):
        catalog=dict(Assets=[asset('wrong',start='unknown')],Houses={})
        p=Program(catalog,self.selection(),set(),60,random.Random(1))
        self.assertFalse(p.events);self.assertTrue(all(s['Pose'] for s in p.character))
    def test_weather_dependencies_and_house_exclusions(self):
        a=asset('umbrella');a['Dependencies']=[['weather:rainy','weather:stormy']]
        self.assertFalse(allowed(a,'house',set(),set(),{}))
        self.assertTrue(allowed(a,'house',set(),{'weather:rainy'},{}))
        self.assertFalse(allowed(a,'house',set(),{'weather:rainy'},{'excludedCharacterMoments':['umbrella']}))
        a['Excluded']=['weather:windy']
        self.assertFalse(allowed(a,'house',set(),{'weather:rainy','weather:windy'},{}))
    def test_night_visitors_never_selected_during_day(self):
        v=asset('stars','idleSceneVisitor',rules=['timeOfDay:lateNight','timeOfDay:evening'])
        catalog=dict(Assets=[v],Houses={})
        self.assertFalse(Program(catalog,self.selection(),{'timeOfDay:afternoon'},60,random.Random(1)).visitors)
        self.assertTrue(Program(catalog,self.selection(),{'timeOfDay:lateNight'},60,random.Random(1)).visitors)
    def test_intro_and_outro_play_once_only_loop_repeats(self):
        a=asset('phased');a['Layers']=[dict(Phase=p,Duration=d) for p,d in [('intro',1),('loop',2),('outro',3)]]
        self.assertEqual([d for _,d in phases(a,3)],[1,6,3])
    def test_no_repeat_before_eligible_pool_exhausted(self):
        items=[asset(str(i),end='a') for i in range(8)]
        p=Program(dict(Assets=items,Houses={}),self.selection(),set(),240,random.Random(2))
        ids=[e['Id'] for e in p.events]
        self.assertGreater(len(ids),3);self.assertEqual(len(ids[:8]),len(set(ids[:8])))

    def test_one_event_lane_with_quiet_sleep_between_events(self):
        items=[asset('action'+str(i),end='a') for i in range(8)]
        items += [asset('visitor'+str(i),'idleSceneVisitor') for i in range(8)]
        p=Program(dict(Assets=items,Houses={}),self.selection(),set(),600,random.Random(12))
        self.assertGreater(len(p.events),5)
        for a,b in zip(p.events,p.events[1:]):
            self.assertNotEqual(a['Visitor'],b['Visitor'])
            self.assertGreaterEqual(b['Time']-a['Time'],27)
        for visitor in p.visitors:
            overlaps=[s for s in p.character if s['Start']<visitor['Start']+visitor['Duration'] and s['Start']+s['Duration']>visitor['Start']]
            self.assertTrue(all(s['Pose'] for s in overlaps))
        self.assertEqual(p.character[-1]['Asset']['Id'],'a')

if __name__=='__main__':unittest.main()
