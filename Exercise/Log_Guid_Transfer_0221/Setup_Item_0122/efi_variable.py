import re


class EfiVariable:

    def __init__(self, cwd_setup_item_folder, project_folder, platform_folder, token_dict, enable_debug=False):
        self.token_dict = token_dict
        self.debug_show = enable_debug
        self.setup_file = cwd_setup_item_folder + '\setup.bin'
        self.bootmanager_file = cwd_setup_item_folder + '\BootManager.bin'
        self.setupamtfeatures_file = cwd_setup_item_folder + '\SetupAmtFeatures.bin'
        self.setup_variable_data_list = []
        self.setup_variable_define_file = platform_folder + '\HardcodedSetupData.h'
        self.setupprep_define_file = project_folder + '\DellPkg\Include\SetupPrep.h'
        self.amivfr_define_file = project_folder + '\AmiTsePkg\Include\AMIVfr.h'
        self.setup_variable_dict = {}
        self.other_variable_dict = {}

        self.buildup_setup_dict()
        self.buildup_other_variable_dict()

    def get_setup_variable_dict(self):
        return self.setup_variable_dict

    def get_other_variable_dict(self):
        return self.other_variable_dict

    def buildup_setup_dict(self):
        self.setup_variable_data_list = EfiVariable.get_binary_file_data(self.setup_file, 0x28)
        # (1) Build/GenericSetupDataDefinition.h insert a field: Numlock
        index = 0
        data = [self.setup_variable_data_list[0]]
        self.setup_variable_dict['Numlock'] = data
        index += 1

        # (2) HardcodedSetupData.h
        with open(self.setup_variable_define_file, "r") as field_define:
            for line in field_define:
                new_line = line.replace(';', '').replace('//', ' // ').split('//')[0]
                new_line_2 = " ".join(new_line.split())
                if re.match('UINT', new_line_2, re.IGNORECASE) or re.match('CHAR', new_line_2, re.IGNORECASE):
                    field_size = EfiVariable.get_field_size(new_line_2)
                    if re.search('\[', new_line_2, re.IGNORECASE):
                        new_line_2_list = new_line_2.split('[',)
                        new_line_3 = " ".join(new_line_2_list[0].split())
                        new_line_3_list = new_line_3.split(' ')
                        key = new_line_3_list[1]
                        array_number = new_line_2_list[1].split(']')[0].strip()
                        if re.search('0x', array_number, re.IGNORECASE):
                            array_number = int(array_number, 16)  # int(STRING, BASE)
                        else:
                            array_number = int(array_number)
                        # print('##index', hex(0x28 + index))
                        array_data = ['ARRAY']
                        for j in range(array_number):
                            data = []
                            for i in range(field_size):
                                data.append(self.setup_variable_data_list[index])
                                index += 1
                            array_data.append(data)
                        # print('##key', key, '##array_number', array_number, '##array_data', array_data)
                        self.setup_variable_dict[key] = array_data
                    else:
                        new_line_2_list = new_line_2.split(' ')
                        key = new_line_2_list[1]
                        data = []
                        # print('@@index', hex(0x28 + index))
                        for i in range(field_size):
                            data.append(self.setup_variable_data_list[index])
                            index += 1
                        # print('@@key', key, '@@data', data)
                        self.setup_variable_dict[key] = data
        if self.debug_show:
            self.show_setup_variable_dict()
            print('### setup_variable_dict: data size',  len(self.setup_variable_data_list), ' data used:', index)

    def buildup_other_variable_dict(self):
        # 1.0 AMITSEMODE
        # I can't find AmiTseMode variable under UEFI shell
        # Current i set all fields' value to 0 (default value)
        field_structure = self.get_focus_data_struct('AMITSEMODE', self.setupprep_define_file)
        for index in range(0, len(field_structure), 2):
            self.other_variable_dict['AMITSEMODE.' + field_structure[index]] = '0'

        # 1.1 BOOT_MANAGER
        field_structure = self.get_focus_data_struct('BOOT_MANAGER', self.amivfr_define_file)
        data = EfiVariable.get_binary_file_data(self.bootmanager_file, 0x34)
        for index in range(0, len(field_structure), 2):
            if field_structure[index+1] == 2:
                a0 = int(str(data[0]), 16)
                a1 = int(str(data[1]), 16)
                value = a1 + a0
            else:
                value = int(str(data[0]), 16)
            self.other_variable_dict['BOOT_MANAGER.' + field_structure[index]] = value

        # 1.2 SETUP_AMT_FEATURES
        # Structure is under chipset folder KabylakePlatSamplePkg\Setup\MeSetup.h'
        # this tool is cross platform. so i just copy the structure from this file
        field_structure = ['GrayOut', 1]
        data = EfiVariable.get_binary_file_data(self.setupamtfeatures_file, 0x3e)
        self.other_variable_dict['SETUP_AMT_FEATURES.' + field_structure[index]] = int(str(data[0]), 16)
        if self.debug_show:
            print('### other_variable_dict:', self.other_variable_dict.items())

    def get_field_value(self, field):
        value = 'N/A'
        if re.search('\[', field, re.IGNORECASE):
            data_list = field.replace('[', ' ').replace(']', ' ').strip().split(' ')
            field_value = self.setup_variable_dict.get(data_list[0], 'N/A')
            if field_value != 'N/A':
                index = self.token_dict.get(data_list[1], 'N/A')
                if index != 'N/A':
                    if field_value[0] == 'ARRAY':
                        index = int(index) + int(1)
                    value = field_value[int(index)]
        else:
            value = self.setup_variable_dict.get(field, 'N/A')
        return value

    @staticmethod
    def get_binary_file_data(file_name, start_index):
        with open(file_name, "rb") as binary_file:
            binary_file.seek(start_index)
            b_data = binary_file.read()
            data = bytearray(b_data)
        return data

    @staticmethod
    def get_field_size(line):
        size = 0
        if re.match('UINT8', line, re.IGNORECASE):
            size = 1
        elif re.match('UINT16', line, re.IGNORECASE):
            size = 2
        elif re.match('UINT32', line, re.IGNORECASE):
            size = 4
        elif re.match('UINT64', line, re.IGNORECASE):
            size = 8
        elif re.match('CHAR8', line, re.IGNORECASE):
            size = 1
        elif re.match('CHAR16', line, re.IGNORECASE):
            size = 2
        return size

    def get_focus_data_struct(self, struct_name, struct_location):
        field_structure = []
        with open(struct_location, "r") as target_file:
            target_file_iter = iter(target_file)
            for line in target_file_iter:
                if re.search('typedef', line, re.IGNORECASE) and re.search('struct', line, re.IGNORECASE):
                    data_structure = []
                    leave_flag = False
                    record_flag = False
                    for next_line in target_file_iter:
                        next_line = next_line.replace(';', '').strip()
                        new_line = ' '.join(next_line.split())
                        if leave_flag:
                            break
                        if re.match('}', new_line, re.IGNORECASE):
                            if re.search(struct_name, new_line, re.IGNORECASE):
                                break
                            else:
                                leave_flag = True
                                continue
                        if re.match('{', new_line, re.IGNORECASE):
                            new_line = new_line.replace('{', '')
                            record_flag = True
                        if record_flag and new_line != '':
                            data_structure.append(new_line)
                    if re.search(struct_name, new_line, re.IGNORECASE):
                        for data in data_structure:
                            data_list = data.split(' ')
                            field_structure.append(data_list[1])
                            field_structure.append(self.get_field_size(data_list[0]))
                        break
        return field_structure

    def show_setup_variable_dict(self):
        print('~~~~~~~~~~setup_variable_dict~~~~~~~~~~~~~~~~~~')
        field_list = list(self.setup_variable_dict.keys())
        for i in field_list:
            print('Field:', i)
            value = self.setup_variable_dict[i]
            if value[0] == 'ARRAY':
                for array_index in range(1, len(value)):
                    print('value_' + str(array_index) + ':', value[array_index])
            else:
                print('Value:', value)


if __name__ == '__main__':
    target_project_folder = 'c:\BIOS\Rugged2\Liv2_99.0.41_Rev0901_BT'
    token_dict = {}
    efi_variable = EfiVariable(target_project_folder, token_dict, True)
    setup_variable_dict = efi_variable.get_setup_variable_dict()
    other_variable_dict = efi_variable.get_other_variable_dict()