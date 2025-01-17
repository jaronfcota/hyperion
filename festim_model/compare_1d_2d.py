import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import pint
import h_transport_materials as htm

from run_comparison import T_values, salt_diameter, salt_thickness, thicknesses, diameters, T_val
from festim_model_copy import downstream_flux_salt, P_up
from scipy.optimize import curve_fit

import itertools

ureg = pint.UnitRegistry()
ureg.setup_matplotlib()

# WORKFLOW
# Adjust pressure in festim_model(_copy)
# Then run run_comparison.py

salt_volume = salt_thickness * ureg.m * (salt_diameter * ureg.m / 2) ** 2 * np.pi

print(f"Salt volume: {salt_volume.to(ureg.ml)}")

plt.gca().xaxis.set_units(ureg.hour)

cmap = plt.get_cmap("Reds")

norm = Normalize(vmin=620, vmax=900)

# Flibe mat props
flibe_diffusivity = htm.diffusivities.filter(material=htm.FLIBE, author='calderoni')[0]
flibe_solubility = htm.solubilities.filter(material=htm.FLIBE, author='calderoni')[0]
flibe_permeability = htm.permeabilities.filter(material=htm.FLIBE).mean()


def prop_errors(flux, times, salt_thickness, temp, P_up, plot = False):
    '''
    Function for quantifying the error between the observed properties and the properties
    that are calculated with the barrier

    Returns a dictionary of "diffusivity error", "solubility error", and "permeability error"

    flux: flux of the surface that you're evaluating, given by run_comparison.py (i.e. flux_2d)
    times: times given by run_comparison.py (i.e. t_2d)
    salt_thickness: the length of flibe [meters]
    temp: the temperature of the experiment [Kelvin]

    '''
    # Providing a guess for the curve_fit function, which is the (measured perm, measured diff)
    guess = (flibe_solubility.value(temp).magnitude*flibe_diffusivity.value(temp).magnitude, flibe_diffusivity.value(temp).magnitude)


    # Using a lambda function so that the length and the pressure are not being fit
    props, cov = curve_fit(lambda t, permeability, D: downstream_flux_salt(t, P_up, salt_thickness, permeability, D), times, np.abs(flux), guess)    
    #print('permeability: ', props[0], 'diffusivity: ', props[1])
    # The calculated solubility and permeability
    perm = flibe_diffusivity.value(temp).magnitude * flibe_solubility.value(temp).magnitude
    sol = props[0]/props[1]

    # The error calculations
    diff_error = (flibe_diffusivity.value(temp).magnitude - props[1])/flibe_diffusivity.value(temp).magnitude*100
    sol_error = (flibe_solubility.value(temp).magnitude - sol)/flibe_solubility.value(temp).magnitude*100
    perm_error = (perm - props[0])/perm*100
    if plot:
        # Having each simulation have the same color on the plot
        marker = itertools.cycle(('o', 'v', '^', '<', '>', 's', '8', 'p'))
        line=plt.plot(times, downstream_flux_salt(times, P_up, salt_thickness, *props), linestyle='', markeredgecolor='none', marker=next(marker))
        linecolor = line[0].get_color()

        # Constructing the plots
        plt.scatter(times, np.abs(flux), alpha=0.3, label=f"2D", marker = ".", color=linecolor)
        plt.plot(times, downstream_flux_salt(times, P_up, salt_thickness, *props), label=f"2D curve fit", linestyle = "dashed", color=linecolor)
        plt.plot(times, downstream_flux_salt(times * htm.ureg.sec, P_up * htm.ureg.Pa,permeability=flibe_diffusivity.value(temp)*flibe_solubility.value(temp), L=salt_thickness*htm.ureg.m, D=flibe_diffusivity.value(temp)), label=f"1D", color=linecolor)
        plt.legend()
        plt.show()
    return {"diffusivity error": diff_error, "solubility error": sol_error, "permeability error": perm_error }

thicknesses = np.linspace(2e-3, 15e-3, num=14)
diameters = np.linspace(20e-3, 100e-3, num=9)
if __name__ == "__main__":
    
    errors = {"temperatures": T_values,
          "thickness": thicknesses,
          "diffusivity error": [],
          "solubility error": [],
          "permeability error": []}

    # Change these if changing temperature or changing thickness/diameters
    T_plot = False
    thickness_comp = True
    if T_plot:

        for T in T_values:
            data_1d = np.genfromtxt(
                f"2D_model/{T:.0f}K/1d/derived_quantities.csv", delimiter=",", names=True
            )
            data_2d = np.genfromtxt(
                f"2D_model/{T:.0f}K/2d/derived_quantities.csv", delimiter=",", names=True
            )


            t_1d = data_1d["ts"] * ureg.s
            t_2d = data_2d["ts"] * ureg.s
            # Adjusted the flux id to "solute_flux_surface_3"
            # Also dividing by the area of the permeating surface to get the same units as the 1D simulations
            flux_1d = np.abs(data_1d["solute_flux_surface_3"]) * ureg.particle * ureg.s**-1 / np.pi / (salt_diameter/2)**2 * ureg.m**-2
            flux_2d = np.abs(data_2d["solute_flux_surface_3"]) * ureg.particle * ureg.s**-1 / np.pi / (salt_diameter/2)**2 * ureg.m**-2
            # Calculating the lateral flux
            # Dividing by area of cylinder wall
            flux_lateral = np.abs(data_2d["solute_flux_surface_2"]) * ureg.particle * ureg.s**-1 / np.pi / salt_diameter / salt_thickness * ureg.m**-2
            flux_bottom = data_2d["solute_flux_surface_1"] * ureg.particle * ureg.s**-1 / np.pi / (salt_diameter/2)**2 * ureg.m**-2

            plt.plot(t_1d, flux_1d, color=cmap(norm(T)))
            plt.plot(t_2d, flux_2d, color=cmap(norm(T)), linestyle = "dashed")
            #plt.plot(t_2d, flux_lateral, color =cmap(norm(T)), linestyle = 'dotted')

            plt.fill(
                np.append(t_1d, t_2d[::-1]),
                np.append(flux_1d, flux_2d[::-1]),
                alpha=0.5,
                color=cmap(norm(T)),
            )

            plt.annotate(
                f"  {T:.0f} K", (t_1d[-1], (flux_1d[-1] + flux_2d[-1]) / 2), color=cmap(norm(T))
            )


            # Calculating errors
            errors["diffusivity error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, salt_thickness, T, P_up, plot = False)['diffusivity error'])
            errors["solubility error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, salt_thickness, T, P_up)['solubility error'])
            errors["permeability error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, salt_thickness, T, P_up)['permeability error'])


        plt.xlabel(f"Time ({plt.gca().xaxis.get_units()})")
        plt.ylabel(f"Permeation flux ({plt.gca().yaxis.get_units():~P})")
        plt.title(f"1D vs. 2D at $\ell$ = {salt_thickness*1000:.2f}mm, $d$ = {salt_diameter*1000:.2f}mm")
        plt.xlim(left=0)
        plt.ylim(bottom=0)

        plt.gca().spines[["right", "top"]].set_visible(False)

        plt.show()


        plt.plot(errors['temperatures'], errors['permeability error'])
        plt.xlabel("Temperature (K)")
        plt.ylabel("Error (%)")
        plt.title("diff error as a function of temperature")
        plt.show()

    if thickness_comp:
        overall_error = {
            "temperatures": T_values,
            "thicknesses": thicknesses,
            "diffusivity error": [],
            "solubility error": [],
            "permeability error": [] 
        }

        # Array that contains the flux difference
        flux_difference_total = []

        norm = Normalize(vmin = thicknesses[0]-1e-3, vmax = thicknesses[-1]+1e-3)
        for diameter in diameters:
            errors = {"temperatures": T_values,
            "thickness": thicknesses,
            "diffusivity error": [],
            "solubility error": [],
            "permeability error": []
            }
            
            # Individual difference per diameter
            flux_diff = []
            for thickness in thicknesses:
                data_1d = np.genfromtxt(
                    f"2D_model/{thickness*1000:.2f}mm_thick_{diameter*1000:.2f}mm_wide/1d/derived_quantities.csv", delimiter=",", names=True
                )
                data_2d = np.genfromtxt(
                    f"2D_model/{thickness*1000:.2f}mm_thick_{diameter*1000:.2f}mm_wide/2d/derived_quantities.csv", delimiter=",", names=True
                )
                t_1d = data_1d["ts"] * ureg.s
                t_2d = data_2d["ts"] * ureg.s
                # Adjusted the flux id to "solute_flux_surface_3"
                # Also dividing by the area of the permeating surface to get the same units as the 1D simulations
                flux_1d = np.abs(data_1d["solute_flux_surface_3"]) * ureg.particle * ureg.s**-1 / np.pi / (diameter/2)**2 * ureg.m**-2
                flux_2d = np.abs(data_2d["solute_flux_surface_3"]) * ureg.particle * ureg.s**-1 / np.pi / (diameter/2)**2 * ureg.m**-2
                # Calculating the lateral flux
                # Dividing by area of cylinder wall
                flux_lateral = np.abs(data_2d["solute_flux_surface_2"]) * ureg.particle * ureg.s**-1 / np.pi / diameter / thickness * ureg.m**-2
                flux_bottom = data_2d["solute_flux_surface_1"] * ureg.particle * ureg.s**-1 / np.pi / (diameter/2)**2 * ureg.m**-2

                flux_diff.append(flux_2d[-1].magnitude - flux_lateral[-1].magnitude)
                '''
                plt.plot(t_1d, flux_1d, color=cmap(norm(thickness)))
                plt.plot(t_2d, flux_2d, color=cmap(norm(thickness)), linestyle = "dashed")
                #plt.plot(t_2d, flux_lateral, color =cmap(norm(thickness)), linestyle = 'dotted')
                plt.fill(
                    np.append(t_1d, t_2d[::-1]),
                    np.append(flux_1d, flux_2d[::-1]),
                    alpha=0.5,
                    color=cmap(norm(thickness)),
                )

                plt.annotate(
                    f"  {thickness*1000:.2f}mm thick", (t_1d[-1], (flux_1d[-1] + flux_2d[-1]) / 2), color=cmap(norm(thickness))
                )
                '''
                # Calculating errors
                
                errors["diffusivity error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, thickness, T_val, P_up, plot = False)['diffusivity error'])
                errors["solubility error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, thickness, T_val, P_up)['solubility error'])
                errors["permeability error"].append(prop_errors(flux_2d.magnitude, t_2d.magnitude, thickness, T_val, P_up)['permeability error'])
                
            '''
            plt.xlabel(f"Time ({plt.gca().xaxis.get_units()})")
            plt.ylabel(f"Permeation flux ({plt.gca().yaxis.get_units():~P})")
            plt.title(f"1D vs. 2D at D = {diameter*1000:.2f}mm")
            plt.xlim(left=0)
            plt.ylim(bottom=0)

            plt.gca().spines[["right", "top"]].set_visible(False)

            plt.show()
            '''
            # plotting the errors

            # Similar technique to making the overall error from 1D_model.ipynb
            overall_error['diffusivity error'].append(errors['diffusivity error'])
            overall_error['permeability error'].append(errors['permeability error'])
            overall_error['solubility error'].append(errors['solubility error'])

            flux_difference_total.append(flux_diff)

    # Creating an error contour like in 1D_model.ipynb
    XX, YY = np.meshgrid(thicknesses*1e3, diameters*1e3)
    ZZ = overall_error['permeability error']

    CF = plt.contourf(XX, YY, ZZ, levels = 100)
    CS = plt.contour(XX,YY,ZZ, levels = 10, colors = 'white')
    plt.clabel(CS, fmt="%.2f")
    plt.xlabel("Thickness (mm)")
    plt.ylabel("Diameter (mm)")
    from matplotlib.cm import ScalarMappable
    plt.colorbar(CF, label = 'Difference (%)')
    plt.title("Permeability error by varying salt thickness and diameter")
    plt.plot([2,10], [20, 100], '--', color = 'yellow')
    plt.annotate("$d/\ell=10$", (5.3, 78), color = 'yellow', fontsize = 12)
    plt.show()

    '''
    # Comparing lateral vs top surface fluxes
    XX, YY = np.meshgrid(thicknesses*1e3, diameters*1e3)
    ZZ = np.array(flux_difference_total)*1e-16

    CF = plt.contourf(XX, YY, ZZ, levels = 100)
    CS = plt.contour(XX,YY,ZZ, levels = 10, colors = 'white')
    plt.clabel(CS, fmt="%.2f")
    plt.xlabel("Thickness (mm)")
    plt.ylabel("Diameter (mm)")
    from matplotlib.cm import ScalarMappable
    plt.colorbar(CF, label = r"Flux difference ($H/m^2/s \cdot 10^{16}$)")
    plt.plot([1,4], [25, 100], '--', color = 'yellow')
    plt.annotate("$d/\ell=25$", (3.3, 70), color = 'yellow', fontsize = 12)
    plt.title("Difference in top and lateral flux")
    plt.show()
    '''