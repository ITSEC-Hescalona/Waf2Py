#!/usr/bin/env python
# Chris - cvaras@itsec.cl
# -*- coding: utf-8 -*-

import network
import stuffs
import subprocess
import os

@auth.requires_login()
def Routes():
    #Routes in OS
    cmd = "/sbin/route -n | head -n 3 | tail -1"
    routes = os.popen(cmd)
    routes_os = routes.read()
    routes_os = routes_os.split()

    #Cut in array
    routes_os.pop(3)
    routes_os.pop(3)
    routes_os.pop(3)
    routes_os.pop(3)

    #Routes in BDD
    routes_db = db(db.routes).select(db.routes.ALL)


    a = network.Network()
    ListIps = a.IpsUsed()
    iface_names = a.iface_names()
    query = db(db.system).select(db.system.iface_ip)

    return dict(routes_os=routes_os, routes_db=routes_db, query=query, iface_names=iface_names, page="Routes", icon="fa fa-arrows", title="Manage static routes")

@auth.requires_login()
def VirtualIps():

    return dict(page="Manage virtual IPs", icon="fa fa-pencil", title="Remove a Virtual IP")

@auth.requires_login()
def VirtualIpsList():
    ips = network.Network()
    ifconf_ip = ips.IpsUsed()
    query = db(db.system).select(db.system.iface_ip, db.system.iface_name, db.system.used_by, db.system.available)
    ips_list = []
    for row in query:
        ips_list.append(dict(iface_ip=row['iface_ip'], iface_name=row['iface_name'], used_by=row['used_by'], available=row['available']))

    return response.json({'ips':ips_list})

@auth.requires_login()
def AddVirtualIps():

    a = network.Network()
    ListIps = a.IpsUsed()
    iface_names = a.iface_names()


    return dict(ListIps=ListIps, iface_names=iface_names, page="Virtual IPs", icon="fa fa-pencil", title="Add Virtual IP")

@auth.requires_login()
def AddInterface():
    n = network.Network()
    iface_names = n.iface_names()
    a = stuffs.Filtro()
    b = a.CheckStrIP(request.vars['ip'])

    mask = a.CheckStrIP(request.vars['mask'])
    if b == 'YES' and mask == 'YES' and request.vars['name'] in iface_names and len(request.vars['ip']) <= 45:
        query = db(db.system.iface_ip == request.vars['ip']).select(db.system.iface_ip, db.system.iface_name)
        if not query:
            try:

                c = n.AddIface(request.vars['ip'], request.vars['mask'], request.vars['name'])


                if 'Interface' in c['message']:
                    session.flash = 'Interface Added!'
                    db.system.insert(iface_ip=str(request.vars['ip']),
                                          iface_name=c['device'])
                else:
                    session.flash = c['message']
            except Exception as e:
                response.flash = str(e)
                #print e
        else:
            session.flash = 'Virtual IP exist'
    else:
        response.flash = 'Error in data suplied'

    return dict()

@auth.requires_login()
def DelInterface():


    a = stuffs.Filtro()
    b = a.CheckStrIP(request.vars['iface_ip'])

    if b == 'YES':

        #get ip data
        query = db(db.system.iface_ip == request.vars['iface_ip']).select(db.system.used_by, db.system.iface_name)
        gw = os.popen("route | awk '{print $8}'")
        for i in gw:
            try:
                if query[0]['iface_name'] in i:
                    session.flash = "You CAN'T DELETE Main Interface >:("
                    redirect(URL('VirtualIps'))
            except:
                redirect(URL('VirtualIps'))

        try:
            #check if ip is being used
            a = query[0]['used_by']
            if a != None:
                session.flash = "Interface is being used by %s" %(a)
                r = "Interface is being used by %s" %(a)
            else:

                subprocess.Popen(['sudo','ifconfig', query[0]['iface_name'], 'down'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                db(db.system.iface_ip == request.vars['iface_ip']).delete()
                session.flash = 'Virtual Ip removed'

                r = 'Virtual Ip removed'
        except:
            session.flash = 'Error in data supplied'
            r = 'Error in data supplied'

    return response.json(data=r)

@auth.requires_login()
def AddGateway():

    #Get IP Default Gateway
    cmd_ipgateway = "/sbin/ip route | awk '/default/ { print $3 }'"
    default_gateway = subprocess.Popen(cmd_ipgateway, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    default_gateway, err = default_gateway.communicate()
    if err:
        response.flash = err
        return

    #Check vars
    a = stuffs.Filtro().CheckStrIP(request.vars['ip'])
    b = stuffs.Filtro().CheckStrIP(request.vars['gateway'])
    c = stuffs.Filtro().CheckName(request.vars['iface'])

    #eprint str(default_gateway.splitlines()[0]) + " " + request.vars['gateway']
    #Validate vars
    if a == 'YES' and b == 'YES' and c == 'YES' and str(default_gateway.splitlines()[0]) != str(request.vars['gateway']):
        process = subprocess.Popen(['sudo', '/sbin/route', 'add', request.vars['ip'], 'gw', request.vars['gateway'], 'dev', request.vars['iface']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process,err = process.communicate()
        if err:
            response.flash = err
            return
        a = stuffs.Stuffs().password()
        db.routes.insert(id_rand = a,
                        ip = request.vars['ip'],
                        gw_ip = request.vars['gateway'],
                        iface = request.vars['iface'])
    else:
        session.flash = 'Error in data supplied'
        return

    #redirect(URL('Routes'))
    session.flash = "Routes Added"

    return


@auth.requires_login()
def DeleteRoute():
    #Check vars
    a = stuffs.Filtro().CheckStr(request.vars['id'])
    if a != 'YES':
        session.flash = 'Error in data supplied'
        return

    query = db(db.routes.id_rand == request.vars['id']).select(db.routes.ip, db.routes.gw_ip, db.routes.iface)
    process = subprocess.Popen(['sudo', '/sbin/route', 'del', query[0]['ip'], 'gw', query[0]['gw_ip'], 'dev', query[0]['iface']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process,err = process.communicate()
    if err:
        session.flash = err
        return

    db(db.routes.id_rand == request.vars['id']).delete()

    #redirect(URL('Routes'))
    session.flash = 'Route Deleted'

    return
