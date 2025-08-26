# **Modbus Server App**

Modbus Server App emulates a Modbus TCP device running in your system terminal with a TUI (Terminal User Interface).

# About
The Modbus Server App is designed to act as a PLC running a Modbus TCP server. The interface is based on Watch Window of Mitsubishi GX Works 3 software, where user can put memory address of a memory bit (M type device) and 16bit register (D type device) and change it value at any time.

This is useful to reduce programming time when a project needs integration of a PC and a PLC in the case of the PLC is not available to the software engineer, allowing that programming logic been tested early.

**Key highlights:**

- Allow that programming logic been tested and bug fixing early.

- Python script that run directly in terminal with a intuitive user interface using [Textual](https://textual.textualize.io/) package.
- Can be used both in Windows OS and Linux distributions.

# **Installation**
**Prerequisites**

- Python 3 or higher
- Textual 0.63.6 or higher
- PyModbus 3.8.1
- Rich 13.7.1


**Steps**

Clone the repository:

```bash
git clone https://github.com/your-username/your-project.git
cd modbus_server_app
```

Install dependencies with `pip` or your favorite PyPI package manager.

```bash
pip install -r requirements.txt
```

# **Usage**
Go to source folder and run the python script.

```bash
cd src
python3 modbus_server.py
```
