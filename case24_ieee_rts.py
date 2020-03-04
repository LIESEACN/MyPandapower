# case24_ieee_rts
import pandas as pd
import numpy as np
import pandapower as pp
'''
Use this code to convert the matpower format to pandapower format

@author : Leung, Canton, China
@Mail : gdyjtlzy@gmail.com

Inspire from pandapower
Thanks to pandapower
About pandapower:https://github.com/e2nIEE/pandapower/blob/v2.2.1/doc/about.rst
'''

dirpath = r'C:\Users\ZIYANG\OneDrive\桌面\研究生\代码管理\pandapower\case24_ieee_rts.xlsx'

case24_xls = pd.ExcelFile(dirpath)
bus = pd.read_excel(case24_xls, 'bus', header=None)
gen = pd.read_excel(case24_xls, 'gen', header=None)
branch = pd.read_excel(case24_xls, 'branch', header=None)
gencost = pd.read_excel(case24_xls, 'gencost', header=None)

# 设置column
bus.columns = ['bus_i', 'type', 'Pd', 'Qd', 'Gs',	'Bs', 'area',
               'Vm', 'Va', 'baseKV',	'zone',	'Vmax',	'Vmin']
gen.columns = ['bus',	'Pg', 'Qg', 'Qmax', 'Qmin', 'Vg', 'mBase', 'status', 'Pmax', 'Pmin', 'Pc1',
               'Pc2', 'Qc1min', 'Qc1max', 'Qc2min', 'Qc2max', 'ramp_agc', 'ramp_10', 'ramp_30', 'ramp_q', 'apf']
branch.columns = ['fbus', 'tbus', 'r', 'x', 'b', 'rateA', 'rateB',
                  'rateC', 'ratio', 'angle', 'status', 'angmin', 'angmax']
gencost.columns = ['costtype', 'startup', 'shutdown', 'n', 'a', 'b', 'c']

# 设置case
baseMVA = 100
hz = 50
case24_ieee_rts = pp.create_empty_network(sn_mva=baseMVA, f_hz=hz)
omega = 2 * np.pi * hz


# bus create
for i in range(bus.shape[0]):
    pp.create_bus(case24_ieee_rts, vn_kv=bus.loc[i, 'baseKV'], name='bus'+str(i+1),
                  type='b', in_service=True,
                  max_vm_pu=bus.loc[i, 'Vmax'], min_vm_pu=bus.loc[i, 'Vmin'])


# gen create
# gen指的是PV节点上的发电机，sgen为PQ节点上的发电机，此处opf可以不管，matpower中一般发电机节点就是PV
# matpower中的平衡节点3，这里在发电机中表现，即是slack为true
for i in range(gen.shape[0]):
    gen_bus = gen.loc[i, 'bus']
    pp.create_gen(
        case24_ieee_rts, bus=gen.loc[i, 'bus']-1, p_mw=gen.loc[i, 'Pg'],
        vm_pu=gen.loc[i, 'Vg'], sn_mva=gen.loc[i, 'mBase'],
        name='gen'+str(i+1),
        max_q_mvar=gen.loc[i, 'Qmax'], min_q_mvar=gen.loc[i, 'Qmin'],
        max_p_mw=gen.loc[i, 'Pmax'], min_p_mw=gen.loc[i, 'Pmin'],
        in_service=gen.loc[i, 'status'], controllable=True,
        slack=True if bus.loc[gen_bus-1, 'type'] == 3 else False
    )

# create load
for i in range(bus.shape[0]):
    pp.create_load(case24_ieee_rts, i,
                   bus.loc[i, 'Pd'], q_mvar=bus.loc[i, 'Qd'])

# create branch trafo
for i in range(branch.shape[0]):
    fb = int(branch.loc[i, 'fbus']) - 1   # py从0开始
    tb = int(branch.loc[i, 'tbus']) - 1   # py从0开始
    fv = int(bus.loc[fb, 'baseKV'])      # from 电压级别
    tv = int(bus.loc[tb, 'baseKV'])      # to 电压级别
    r_b = branch.loc[i, 'r']        # 电阻
    x_b = branch.loc[i, 'x']        # 电抗
    b_b = branch.loc[i, 'b']        # 电导
    s_b = branch.loc[i, 'status']   # 状态
    if (branch.loc[i, 'ratio'] == 0) & (fv == tv):
        # 线路
        Zn = tv**2/baseMVA  # Vn^2/Sn 阻抗基准值
        # Imax = branch.loc[i, 'rataA']   线路电流约束 由线路容量推至电流
        Imax = branch.loc[i, 'rateA']/tv/np.sqrt(3)
        if Imax == 0:
            Imax = np.inf
        pp.create_line_from_parameters(
            case24_ieee_rts, from_bus=fb, to_bus=tb,
            length_km=1, r_ohm_per_km=r_b*Zn,
            x_ohm_per_km=x_b*Zn, c_nf_per_km=b_b/Zn/omega*1e9/2,
            max_i_ka=Imax, type='ol', max_loading_percent=100,
            in_service=s_b
        )
    else:   # 变压器
        if fv >= tv:        # f t 变比k（tap）在高压侧
            h_bus = fb
            h_vn = fv
            l_bus = tb
            l_vn = tv
            tap_side = 'hv'
        else:               # 变比k（tap）在低压侧
            h_bus = tb
            h_vn = tv
            l_bus = fb
            l_vn = fv
            tap_side = 'lv'
        Sn = branch.loc[i, 'rateA']
        Zn = np.sqrt((r_b**2+x_b**2))
        ratio_1 = branch.loc[i, 'ratio']
        if ratio_1 == 0:    # tap不动
            ratio_1 = 0
        else:
            ratio_1 = (ratio_1-1)*100
        i0_percent = -branch.loc[i, 'b'] * 100 * baseMVA / Sn
        vk_percent = np.sign(x_b) * Zn * Sn * 100 / baseMVA
        vkr_percent = r_b * Sn * 100 / baseMVA
        # matpower中变压器的b一般为0
        pp.create_transformer_from_parameters(
            case24_ieee_rts, hv_bus=h_bus, lv_bus=l_bus,
            sn_mva=Sn, vn_hv_kv=h_vn, vn_lv_kv=l_vn,
            vk_percent=vk_percent, vkr_percent=vkr_percent,
            max_loading_percent=100, pfe_kw=0, i0_percent=i0_percent,
            shift_degree=branch.loc[i, 'angle'],
            tap_step_percent=abs(ratio_1) if ratio_1 else np.nan,
            tap_pos=np.sign(ratio_1) if ratio_1 else np.nan,
            tap_side=tap_side if ratio_1 else None, tap_neutral=0 if ratio_1 else np.nan
        )

# cost function
# 暂时没有考虑分段线性，目前仅有多项式
# pandapower中用elements对应gen和sgen表中的顺序，如果gen有10台，那么elements为0-9
for i in range(gencost.shape[0]):
    if gencost.loc[i, 'costtype'] == 2:
        # poly_cost
        # 二项式
        a = gencost.loc[i, 'a']
        b = gencost.loc[i, 'b']
        c = gencost.loc[i, 'c']
        pp.create_poly_cost(
            case24_ieee_rts, element=i, et='gen',
            cp0_eur=c, cp1_eur_per_mw=b, cp2_eur_per_mw2=a,
            cq0_eur=0, cq1_eur_per_mvar=0, cq2_eur_per_mvar2=0
        )
