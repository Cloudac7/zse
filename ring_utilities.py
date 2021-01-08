__all__ = ['atoms_to_graph','get_paths','remove_non_rings','paths_to_atoms']

'''
This module contains utilities to be used by the rings.py module.
'''

import numpy as np
import math

def atoms_to_graph(atoms,index,max_ring):
    '''
    Helper function to repeat a unit cell enough times to capture the largest
    possible ring, and turn the new larger cell into a graph object.

    RETURNS:
    G = graph object representing zeolite framework in new larger cell
    large_atoms = ASE atoms object of the new larger cell framework
    repeat = array showing the number of times the cell was repeated: [x,y,z]
    '''

    # first, repeat cell, center the cell, and wrap the atoms back into the cell
    cell = atoms.get_cell_lengths_and_angles()[:3]
    repeat = []
    for i,c in enumerate(cell):
        if c/2 < max_ring/2+5:
            l = c
            re = 1
            while l/2 < max_ring/2+5:
                re += 1
                l = c*re

            repeat.append(re)
        else:
            repeat.append(1)

    large_atoms = atoms.repeat(repeat)
    center = large_atoms.get_center_of_mass()
    trans = center - large_atoms.positions[index]
    large_atoms.translate(trans)
    large_atoms.wrap()

    # we need a neighborlist (connectivity matrix) before we can make our graph
    from ase import neighborlist
    cutoff = neighborlist.natural_cutoffs(large_atoms, mult = 1.05)
    nl = neighborlist.NeighborList(cutoffs = cutoff, self_interaction=False, bothways = True)
    nl.update(large_atoms)
    matrix = nl.get_connectivity_matrix(sparse=False)

    # now we make the graph
    import networkx as nx
    G = nx.from_numpy_matrix(matrix)

    return G, large_atoms, repeat

def get_paths(G,index,ring_sizes):
    '''
    Get all the paths (rings) between the index atom and its neighbor
    '''

    # first find the neighbor
    import networkx as nx
    neighbors = [n for n in nx.neighbors(G,index)]
    neighbor = neighbors[0]

    # next find all paths connecting index and neighbor
    paths = []
    for path in nx.all_simple_paths(G,index,neighbor,cutoff=max(ring_sizes)-1):
        if len(path) in ring_sizes:
            paths.append(path)

    return paths

def remove_non_rings(atoms, paths):
    # turn each path into a circular array to find and remove any duplicates
    paths = remove_dups(paths)

    # remove paths that contain smaller rings becuase these are likely not
    # actual rings
    # there are a ton of rules I have written to find these "secondary rings"
    # there is probably a better way to do this, I would love other's input.
    paths = remove_sec(paths)

    # this part is a trick to cut out some of the paths that are just
    # random walks through the framework, and not actual rings
    # here, we assume that fir any T-T-T angle in a path is less than 100, that
    # path can not be a true 8-MR or larger.
    delete = []
    for j,r in enumerate(paths):
        flag = False
        if len(r) > 16:
            r2 = r.copy()
            for x in r[:4]:
                r2.append(x)
            for i in range(1, len(r2)-3,2):
                angle = int(round(atoms.get_angle(r2[i],r2[i+2],r2[i+4],mic=True)))
                if angle < 100:
                    delete.append(j)
                    break
    tmp_paths = paths.copy()
    paths = []
    for j,r in enumerate(tmp_paths):
        if j not in delete:
            paths.append(r)

    return paths

def remove_dups(paths):
    '''
    This is a helper function for get_orings and get_trings.
    '''
    d = []
    for i in range(len(paths)):
        for j in range((i+1), len(paths)):
            if i != j:
                st1 = set(paths[i])
                st2 = set(paths[j])
                if st1 == st2:
                    d.append(int(j))
    tmp_paths = []
    for i in range(len(paths)):
        if i not in d:
            tmp_paths.append(paths[i])
    paths = tmp_paths
    return paths

def remove_sec(paths):
    '''
    This is a helper function for get_orings and get_trings.
    '''
    d = []
    count2 = np.zeros(len(paths))

    for i in range(len(paths)):
        for j in range(i+1,len(paths)):
            if i!= j:
                ringi = paths[i]
                ringj = paths[j]
                ni = len(ringi)
                nj = len(ringj)
                if ni > nj and ni >= 16 and nj > 6:
                    count=0
                    for rj in ringj:
                        if rj in ringi:
                            count+=1
                    if count == nj/2:
                        count2[i]+=1
                    elif count > nj/2:
                        count2[i]+=2
                if nj >ni and nj >= 16 and ni > 6:
                    count=0
                    for ri in ringi:
                        if ri in ringj:
                            count+=1
                    if count == ni/2:
                        count2[j]+=1
                    elif count > ni/2:
                        count2[j]+=2
                if ni > nj and nj in [6,8]:
                    count=0
                    for rj in ringj:
                        if rj in ringi:
                            count+=1
                    if count >= nj-2:
                        count2[i]+=2
                if nj > ni and ni in [6,8]:
                    count=0
                    for ri in ringi:
                        if ri in ringj:
                            count+=1
                    if count >= ni-2:
                        count2[j]+=2
    for i,c in enumerate(count2):
        if c >=2:
            d.append(i)
    tmp_paths = []
    for i in range(len(paths)):
        if i not in d:
            tmp_paths.append(paths[i])
    paths = tmp_paths
    return paths

def paths_to_atoms(atoms,paths):
    keepers = []
    for i in paths:
        for j in i:
            if j not in keepers:
                keepers.append(j)
    d = [atom.index for atom in atoms if atom.index not in keepers]
    del atoms[d]

    return atoms
