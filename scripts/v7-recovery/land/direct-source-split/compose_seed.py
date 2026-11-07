"""Streaming research primitive for composing a full-width candidate seed.

The caller must authenticate and pin every input, validate selected snapshot and
component provenance, provide a partial seed excluding the target root, and
supervise resources. This function neither reads an old output nor approves a
pipeline switch. It emits end-coded runs through a caller-supplied writer.
"""
from compose import compose_row


def compose_streams(partial_rows,direct_rows,component_rows,root,width,height,allowed_codes,write_row,guard):
    if not all(callable(x) for x in (partial_rows,direct_rows,component_rows,write_row,guard)):
        raise ValueError('row providers, writer and guard are required')
    if type(root) is not int or root<0 or type(height) is not int or height<=0:
        raise ValueError('invalid component or grid')
    count=0
    for y in range(height):
        if y%64==0:guard()
        components=component_rows(y);last=0;selected=[]
        for a,b,k in components:
            if any(type(x) is not int for x in (a,b,k)) or not 0<=a<b<=width or a<last:raise ValueError('invalid component spans')
            last=b
            if k==root:selected.append((a,b))
        sparse=direct_rows(y)
        combined=compose_row(partial_rows(y),sparse,selected,width,allowed_codes)
        write_row(y,combined);count+=sum(b-a for a,b in selected)
    guard()
    return {'status':'research-composition-not-a-build','selected_cells':count,'rows':height}
