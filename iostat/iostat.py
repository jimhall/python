#!/Users/jameshall/anaconda3/bin/python

import re
from collections import OrderedDict
#from datetime import datetime
import datetime
from dateutil.parser import parse
import xlsxwriter

def mkTimes(starttime, iotuple):
    sampletimes = [] 
    st = parse(starttime)
    sampletimes.append(st)
    cmd, interval, samples = iotuple
    interval = int(interval)
    samples  = int(samples )
    incremented_t = [st + datetime.timedelta(seconds=x) for x in
    range(interval, interval*samples, interval)]

    sampletimes.extend(incremented_t)
    return(sampletimes)

def patterned_range(myfile, startpat, endpat=None):
    startpat = re.compile(startpat)
    if endpat is not None:
        endpat = re.compile(endpat)
    in_range = False
    for line in myfile:
        if re.match(startpat, line):
            in_range = True
        if in_range:
            yield line
        if endpat is not None and re.match(endpat, line):
            break

def mk_spreadsheet(ioctrltables):
    wkbk = xlsxwriter.Workbook('./testdata/c18.xlsx', {'remove_timezone': True,
                                                       'default_date_format':
                                                       'hh:mm:ss'})
    worksheet = wkbk.add_worksheet()
    lastrow = len(ioctltables['c18']) + 1
    lastcol = len(ioctltables['c18'][0]) + 1
    t = '=ctlrc18'

    options = {'data': ioctltables['c18'],
               'total_row': 1, 'name': 'ctlrc18',
               'columns': [{'header': 'Time'},
                           {'header': 'r/s',
                            'total_function': 'average'},
                           {'header': 'w/s',
                            'total_function': 'average'},
                           {'header': 'kr/s',
                            'total_function': 'average'},
                           {'header': 'kw/s',
                            'total_function': 'average'},
                           {'header': 'wait',
                            'total_function': 'average'},
                           {'header': 'actv',
                            'total_function': 'average'},
                           {'header': 'wsvc_t',
                            'total_function': 'average'},
                           {'header': 'asvc_t',
                            'total_function': 'average'}]}
    worksheet.add_table(2, 2, lastrow, lastcol, options)
    chart = wkbk.add_chart({'type': 'line'})
    chart.add_series({
                      'categories': t + '[Time]',
                      #'categories': '=ctlrc18[Time]',
# Alternate           'categories': '=ctlrc18[[#Data],[Time]]',
# Alternate           'categories': ['Sheet1', 3, 2, lastrow, 2],
                      'values': '=ctlrc18[w/s]',
# Alternate           'values': ['Sheet1', 3, 3, lastrow, 3],
                      'name': 'Write IO Activity'
                      })
    chart.add_series({
                      'categories': '=ctlrc18[Time]',
                      'values': '=ctlrc18[r/s]',
                      'name': 'Read IO Activity'
                      })
    worksheet.insert_chart(2, lastcol + 2, chart)
    wkbk.close()

iostatcmd = r'^/usr/bin/iostat'
iostatopt = r' (-.*) (\d+) (\d+)$'
iostatre = re.compile(iostatcmd + iostatopt)

startcycle = r'(.*) - started$'
startcyclere = re.compile(startcycle)
endcycle   = r'(.*) - ended$'
endcyclere = re.compile(endcycle)
junklines  = r'^$|/usr/bin/iostat|^\s+extended device|^<<|.*:.*\/.*$|.*:.*\)$'
junklines2  = '|.*\snfs\d\d+$|.*rmt\/\d+$|.*ssd\d+\,h$'
junklinesre = re.compile(junklines + junklines2)

with open('testdata/iostat-xpnC.out', 'rt') as fin:
    lines = fin.readlines()
    starttimes = []
    endtimes   = []
    sampbyst   = OrderedDict()

    iostatstring = lines[0]
    if iostatre.match(iostatstring):
        iostatstring = iostatstring.rstrip()
        m = iostatre.match(iostatstring)
        iotuple = (m.group(1), m.group(2), m.group(3))
        print(iotuple)
    else:
        print('No iostat found --> program error?')
        exit()

    for line in lines:
        line = line.rstrip()
        if startcyclere.match(line):
            m = startcyclere.match(line)
            starttimes.append(m.group(1))
        elif endcyclere.match(line):
            m = endcyclere.match(line)
            endtimes.append(m.group(1))

    I = [i for i, x in enumerate(lines) if junklinesre.match(x)]
    for i in sorted(I, reverse=True):
        del lines[i]

    for st, et in zip(starttimes, endtimes):
        stre = re.escape(st) + r' - started$'
        etre = re.escape(et) + r' - ended$'
        sampbyst[st] = []
        for line in patterned_range(lines, stre, etre):
            line = line.rstrip()
            sampbyst[st].append([line])

    ioctltables = {}
    for st in sampbyst:
        for line in sampbyst[st]:
            if re.match(r'.*c\d+$', line[0]):
                m = re.match(r'.*(c\d+$)', line[0])
                ioctltables[m.group(1)] = []

    for st in sampbyst:
        samptimelist = mkTimes(st, iotuple)
        for line in sampbyst[st]:
            if re.match(r'.*c\d+$', line[0]):
                m = re.match(r'.*(c\d+$)', line[0])
                text = re.sub(r'^\s+',r'', line[0])
                data = text.split()
                data = [float(data[x]) for x in range(0,8)]
                data.insert(0, currenttime)
                ioctltables[m.group(1)].append(data)
            elif re.match(r'^\s+r\/s', line[0]):
                currenttime = samptimelist.pop(0)

    mk_spreadsheet(ioctltables)
