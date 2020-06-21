'''
@Liesea CN
A modified case for test based on PandaPower
'''

import pandapower.networks as pn
import numpy as np
import Data
import pandapower as pp
import pandas as pd


def InitialCase():
    '''
    return: pandapower net
    '''
    # Reference Case Based on Case24
    net = pn.case24_ieee_rts()

    # replace
    pp.replace_ext_grid_by_gen(net)
    pp.replace_sgen_by_gen(net)
    # sort the gen
    net.gen = net.gen.sort_values(by=['bus', 'max_p_mw'])
    idx = net.poly_cost.index.to_list()   # idx after sorting
    element = net.poly_cost['element'].to_list()
    net.gen.loc[0, 'slack'] = True

    # modify Gen Parameter according bus order
    for i in range(net.gen.shape[0]):
        net.gen.iloc[i, 10] = Data.PMAX[i]
        net.gen.iloc[i, 11] = Data.PMIN[i]
        net.gen.iloc[i, 12] = Data.QMAX[i]
        net.gen.iloc[i, 13] = Data.QMIN[i]

    # adding a bus for DC line
    pp.create_bus(net,
                  vn_kv=230,
                  name='DCnode',
                  index=24,
                  max_vm_pu=1.05,
                  min_vm_pu=0.95)
    # adding a ext_grid as DC power
    pp.create_ext_grid(net,
                       bus=24,
                       vm_pu=1.05,
                       max_q_mvar=10,
                       min_q_mvar=0,
                       min_p_mw=0,
                       max_p_mw=1000,
                       slack=False)
    # adding cost of ext_grid
    pp.create_poly_cost(net,
                        element=0,
                        et='ext_grid',
                        cp0_eur=0,
                        cp1_eur_per_mw=0,
                        cp2_eur_per_mw2=0)

    # adding DC line
    pp.create_dcline(net,
                     from_bus=24,
                     to_bus=16,
                     p_mw=0,
                     loss_mw=5,
                     loss_percent=5,
                     vm_from_pu=1.05,
                     vm_to_pu=0.95,
                     name='DC1',
                     max_p_mw=400,
                     max_q_from_mvar=0,
                     min_q_from_mvar=0,
                     max_q_to_mvar=0,
                     min_q_to_mvar=0)

    # load
    net.load['controllable'] = True
    # load-sheeding cost and load constraints
    for i in range(net.load.shape[0]):
        net.load.loc[i, 'max_p_mw'] = net.load.loc[i, 'p_mw']
        net.load.loc[i, 'min_p_mw'] = 0
        net.load.loc[i, 'max_q_mvar'] = net.load.loc[i, 'q_mvar']
        net.load.loc[i, 'min_q_mvar'] = 0
        pp.create_poly_cost(net, i, et='load', cp1_eur_per_mw=-500)

    return net, idx, element


def WindPower(ppnet, WindNode, WindPower):
    '''
    风电出力生成
    '''
    def GenerateWind(WindSpeed, WindPowerMax):
        '''
        风速生成风力
        '''
        Vin = 3
        Vr = 13.5
        Vout = 20
        if (WindSpeed <= Vin) and (WindSpeed > Vout):
            return 0
        elif (WindSpeed > Vin) and (WindSpeed <= Vr):
            return WindPowerMax / (Vr-Vin) * WindSpeed - Vin*WindPowerMax/(Vr-Vin)
        elif (WindSpeed > Vr) and (WindSpeed <= Vout):
            return WindPowerMax

    Nw = len(WindNode)
    # index to element
    for i in range(Nw):
        c = 7
        k = 2
        # I = np.where(element == WindNode[i])[0].tolist()
        WindSpeed = c * (-np.log(np.random.rand())) ** (1/k)
        WP = GenerateWind(WindSpeed, WindPower[i])
        ppnet.gen.loc[WindNode[i], 'max_p_mw'] = WP
        ppnet.gen.loc[WindNode[i], 'max_q_mvar'] = WP
        ppnet.gen.loc[WindNode[i], 'min_p_mw'] = 0
        ppnet.gen.loc[WindNode[i], 'min_q_mvar'] = 0

    return ppnet


def ModifyWindCost(net, element, WindNode):
    '''
    找到风机cost位置，修改成本 loc[index]
    '''
    Nw = len(WindNode)
    for i in range(Nw):
        idx = np.where(element == WindNode[i])[0].tolist()
        net.poly_cost.loc[idx, 'cp0_eur'] = 0
        net.poly_cost.loc[idx, 'cp1_eur_per_mw'] = 0
        net.poly_cost.loc[idx, 'cp2_eur_per_mw2'] = 0
    return net


def AddingUnit(net, GEN, COST):
    '''
    增加机组
    '''
    ng = net.gen.shape[0]
    ang = len(GEN)
    for i in range(ang):
        # 增加机组
        pp.create_gen(net,
                      bus=GEN[i][0],
                      p_mw=GEN[i][1],
                      vm_pu=1,
                      index=ng + i,
                      max_q_mvar=GEN[i][3],
                      min_q_mvar=GEN[i][4],
                      max_p_mw=GEN[i][8],
                      min_p_mw=GEN[i][9])
        # 增加成本
        pp.create_poly_cost(net,
                            element=ng + i,
                            et='gen',
                            cp2_eur_per_mw2=COST[i][4],
                            cp1_eur_per_mw=COST[i][5],
                            cp0_eur=COST[i][6])
    return net


def GenStatus(net, Relia):
    '''
    机组可靠性参数
    '''
    Ng = Relia.shape[0]
    for i in range(Ng):
        if np.random.rand() < Relia[i][1]:
            net.gen.iloc[i, 2] = False
    if net.gen.loc[0, 'in_service'] == False:
        # 重新找一个松弛节点
        x = np.where(net.gen['in_service'] == True)[0].tolist()
        x = x[0]
        net.gen.iloc[x, 9] = True
        net.gen.loc[0, 'slack'] = False
    return net


def DCStatus(net, Relia, DCPOWER):
    '''
    直流可靠性参数
    '''
    x = np.random.rand()
    if x < Relia[0]:
        DCPOWER = DCPOWER * 0
    elif x >= Relia[0] and x < Relia[1]:
        DCPOWER = DCPOWER * 0.2
    elif x >= Relia[1] and x < Relia[2]:
        DCPOWER = DCPOWER * 0.4
    elif x >= Relia[2] and x < Relia[3]:
        DCPOWER = DCPOWER * 0.6
    else:
        DCPOWER = DCPOWER
    net.dcline.loc[0, 'max_p_mw'] = DCPOWER
    return net


def SavingResult(path, Data):
    Data = np.array(Data)
    Data = pd.DataFrame(Data)
    writer = pd.ExcelWriter(path)
    Data.to_excel(writer)
    writer.save()
    writer.close()
