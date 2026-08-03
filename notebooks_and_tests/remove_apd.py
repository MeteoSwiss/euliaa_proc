#!/usr/bin/env python3
"""
Simple script to copy HDF5 file excluding APD datasets
"""

import h5py
import sys

def copy_without_apd(input_file, output_file):
    """Copy HDF5 file excluding all APD datasets"""
    
    with h5py.File(input_file, 'r') as src:
        with h5py.File(output_file, 'w') as dst:
            
            # APD datasets to skip
            apd_patterns_to_skip = ['APD1D', 'APD1E', 'APD1N', 'APD1Z', 
                                   'APD2D', 'APD2E', 'APD2N', 'APD2Z',
                                   'fitResErrMieD', 'fitResErrMieE', 'fitResErrMieN', 'fitResErrMieZ',
                                   'fitResMieD', 'fitResMieE', 'fitResMieN', 'fitResMieZ',
                                   ]
            
            def copy_group_recursive(src_group, dst_group, group_path=""):
                """Recursively copy groups and datasets"""
                
                # Copy group attributes
                for key, value in src_group.attrs.items():
                    dst_group.attrs[key] = value
                
                # Process all items in this group
                for key, item in src_group.items():
                    item_path = f"{group_path}/{key}" if group_path else key
                    
                    if isinstance(item, h5py.Group):
                        # Create group and recurse
                        print(f"Creating group: {item_path}")
                        new_group = dst_group.create_group(key)
                        copy_group_recursive(item, new_group, item_path)
                        
                    elif isinstance(item, h5py.Dataset):
                        # Check if this dataset should be skipped
                        if key in apd_patterns_to_skip:
                            print(f"Skipping dataset: {item_path}")
                        else:
                            print(f"Copying dataset: {item_path}")
                            dst_group.copy(item, key)
            
            # Start recursive copy from root
            copy_group_recursive(src, dst)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python remove_apd.py input.h5 output.h5")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Copying {input_file} to {output_file} (excluding APD datasets)")
    copy_without_apd(input_file, output_file)
    print("Done!")