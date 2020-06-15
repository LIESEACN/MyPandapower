import pandapower as pd
import pandapower.networks as pn


# cd D:\OneDrive\桌面\研究生\项目\项目#2 嘉兴供电局 灵活性\资料\code
'''
net = pd.converter.from_mpc('caset.mat',
                            f_hz=50,
                            casename_mpc_file='caset',
                            validate_conversion=False)
'''
net = pn.case24_ieee_rts()
net.load['controllable'] = True
pd.replace_ext_grid_by_gen(net)
pd.replace_sgen_by_gen(net)
net.gen.loc[0, 'slack'] = True
pd.create_bus(net,
              vn_kv=230,
              name='DCnode',
              index=24,
              max_vm_pu=1.05,
              min_vm_pu=0.95)
pd.create_ext_grid(net, bus=24, max_q_mvar=500, min_q_mvar=0, min_p_mw=0, max_p_mw=1000, slack=False)
pd.create_poly_cost(net,
                    element=0,
                    et='gen',
                    cp0_eur=0,
                    cp1_eur_per_mw=0,
                    cp2_eur_per_mw2=0)
pd.create_dcline(net,
                 from_bus=24,
                 to_bus=17,
                 p_mw=400,
                 loss_mw=10,
                 loss_percent=5,
                 vm_from_pu=1.05,
                 vm_to_pu=0.95,
                 name='DC1',
                 max_p_mw=1000,
                 max_q_from_mvar=500,
                 min_q_from_mvar=-500,
                 max_q_to_mvar=500,
                 min_q_to_mvar=-500)

# load-sheeding cost and load constraints
for i in range(net.load.shape[0]):
    net.load.loc[i, 'max_p_mw'] = net.load.loc[i, 'p_mw']
    net.load.loc[i, 'min_p_mw'] = 0
    net.load.loc[i, 'max_q_mvar'] = net.load.loc[i, 'q_mvar']
    net.load.loc[i, 'min_q_mvar'] = 0
    pd.create_poly_cost(net, i, et='load', cp1_eur_per_mw=-500)

pd.runopp(net, verbose=1, numba=True)
