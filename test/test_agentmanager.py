from test import *

class AgentManagerTest(TestCase):
    def test_registration(self):
        NetworkManager.AgentManager.Register('python-network-manager-test')
        NetworkManager.AgentManager.Unregister()

if __name__ == '__main__':
    unittest.main()
