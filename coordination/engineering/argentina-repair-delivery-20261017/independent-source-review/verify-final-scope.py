exec(open('argentina-independent-source-review-20261017/audit.py').read().split('rows=read(')[0])
h=subprocess.check_output(['git','-C',W,'rev-parse','6413fa483e1']).decode().strip();root=P+'source-review/complete-scope-001/'
d=read(root+'source-applicability.json',h);held=read(root+'held-original-keys.json',h);patch=read(root+'requested-native-patch.json',h);rows=read(P+'original-scope/original-intervals.json.gz',h);orig={(y,x,oo[0]):cl for y,a,z,oo,si,cl in rows for x in range(a,z)};hs={(r['y'],r['x'],r['pixelIndex'])for r in held};req={(r['y'],x,o)for r in patch['rows']for a,z,o in r['runs']for x in range(a,z)}
assert len(hs)==len(held)==6149 and len(req)==22697 and not hs&req and hs|req==set(orig)
assert collections.Counter(orig[k]for k in hs)==d['held_classes']and collections.Counter(orig[k]for k in req)==d['remaining_classes'];assert len({k[2]for k in req})==110
for r in d['decisions']:
 i=r['pixelIndex'];assert r['held_cells']==sum(k[2]==i for k in hs)and r['remaining_requested_cells']==sum(k[2]==i for k in req)and r['original_cells']==sum(k[2]==i for k in orig)
assert len(d['decisions'])==len({r['pixelIndex']for r in d['decisions']})==115
law=read(P+'source-review/tdf-law-001/capture.json',h);b=subprocess.check_output(['git','-C',W,'show',h+':'+P+'source-review/tdf-law-001/official-law-1186.html']);assert len(b)==38893==law['bytes']and hashlib.sha256(b).hexdigest()==law['sha256'];s=b.decode();
from html import unescape
text=re.sub('<[^>]+>',' ',unescape(s));text=' '.join(text.split()); print('law context',text[text.find('Sanción'):text.find('Sanción')+400]);print('dates',[(date,date in text)for date in ['27-10-2017','14-11-2017','27/10/2017','14/11/2017']]);print(text[text.find('ARTÍCULO 1'):text.find('ARTÍCULO 1')+700]);
result={'head':h,'partition_exact':True,'original':28846,'held':6149,'requested':22697,'requested_owners':110,'original_owners_retained':115,'held_classes':d['held_classes'],'requested_classes':d['remaining_classes'],'law_sha256':hashlib.sha256(b).hexdigest(),'pending_structured_issue_correction':'CABA applicable_retained_issues omits941'};pathlib.Path('argentina-independent-source-review-20261017/scope-partition-check.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
