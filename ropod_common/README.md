[![pipeline status](https://git.ropod.org/ropod/ropod_common/badges/master/pipeline.svg)](https://git.ropod.org/ropod/ropod_common/commits/master)

# ROPOD Common Repository

## Zyre Communicator
Abstract Base Class to enable comfortable zyre communication through inheritance.

## Install


### Python

After cloning to the repository, install the requirements:

```
sudo pip3 install -r requirements.txt
```

Then install the pyre base class:

```
sudo pip3 install -e .
```

### C++

The C++ base class must be located in `/opt/ropod/`, the recommended way to do it is:

```
git clone git@git.ropod.org:ropod/ropod_common.git
sudo mv ropod_common /opt/ropod/
```
