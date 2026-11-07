"""Compose a sparse direct split with an independently produced partial seed.

The partial seed must already omit the selected component. This module does not
read historical labels or make the partial seed; caller validates all inputs.
"""


def coverage(spans, width, triples, allowed_codes):
    merged=[];last=0
    for item in spans:
        if len(item)!=(3 if triples else 2):raise ValueError('invalid interval fields')
        a,b=item[:2]
        if type(a) is not int or type(b) is not int or not 0<=a<b<=width or a<last:raise ValueError('invalid or overlapping intervals')
        if triples and (type(item[2]) is not int or item[2] not in allowed_codes):raise ValueError('invalid split code')
        if merged and merged[-1][1]==a:merged[-1]=(merged[-1][0],b)
        else:merged.append((a,b))
        last=b
    return merged


def compose_row(seed_runs,split_spans,selected_intervals,width,allowed_codes,*,empty_code=0):
    if type(width) is not int or width<=0 or not seed_runs or not isinstance(allowed_codes,set) or not allowed_codes or empty_code in allowed_codes or any(type(c) is not int or c<0 or c>=2**32 for c in allowed_codes) or type(empty_code) is not int or not 0<=empty_code<2**32:raise ValueError('invalid row or category codes')
    last=0
    for end,code in seed_runs:
        if type(end) is not int or not last<end<=width or type(code) is not int or code not in allowed_codes|{empty_code}:raise ValueError('invalid seed runs')
        last=end
    if last!=width:raise ValueError('seed row does not cover width')
    if coverage(split_spans,width,True,allowed_codes)!=coverage(selected_intervals,width,False,allowed_codes):raise ValueError('split does not exactly cover selected root')
    x=i=j=0;out=[]
    while x<width:
        base_end,base_code=seed_runs[i]
        while j<len(split_spans) and split_spans[j][1]<=x:j+=1
        covered=j<len(split_spans) and split_spans[j][0]<=x
        if covered:
            _,end,code=split_spans[j]
            if base_code!=empty_code:raise ValueError('split overlaps another seed')
            end=min(end,base_end)
        else:
            code=base_code;end=min(base_end,split_spans[j][0]) if j<len(split_spans) else base_end
        if end<=x:raise ValueError('composition made no progress')
        if out and out[-1][1]==code:out[-1]=(end,code)
        else:out.append((end,code))
        x=end
        if x==base_end:i+=1
    return out
