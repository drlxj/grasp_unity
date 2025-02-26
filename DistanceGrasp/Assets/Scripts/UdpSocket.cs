using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;

public class UdpSocket : MonoBehaviour
{
    [HideInInspector] public bool isTxStarted = false;

    [SerializeField] string IP = "127.0.0.1";
    [SerializeField] int rxPort = 20001;
    [SerializeField] int txPort = 20002;

    UdpClient client;
    IPEndPoint remoteEndPoint;
    Thread receiveThread;

    ActionReceiver receiver;

    void Awake()
    {
        // Create remote endpoint (to Matlab) 
        remoteEndPoint = new IPEndPoint(IPAddress.Parse(IP), txPort);

        // Create local client
        client = new UdpClient(rxPort);

        // local endpoint define (where messages are received)
        // Create a new thread for reception of incoming messages
        receiver = FindObjectOfType<ActionReceiver>();
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
    }

    public void SendData(byte[] data)
    {
        try
        {
            client.Send(data, data.Length, remoteEndPoint);
        }
        catch (Exception err)
        {
            Debug.LogWarning(err.ToString());
        }
    }

    // Receive data, update packets received
    private void ReceiveData()
    {
        if (receiver == null) 
        {
            Debug.LogError("Receiver is not assigned.");
        }
        while (true)
        {
            try
            {
                IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);
                byte[] data = client.Receive(ref anyIP);
                receiver.interactor.IsGestureProbability = true;
                receiver.GetMostProbableObjIdx(data);
            }
            catch (SocketException ex)
            {
                if (ex.SocketErrorCode == SocketError.WouldBlock || ex.SocketErrorCode == SocketError.IOPending)
                {
                    receiver.interactor.IsGestureProbability = false;
                    Console.WriteLine("No data received at this time.");
                }
                else
                {
                    Console.WriteLine("SocketException: " + ex.Message);
                }
            }
        }
    }


    //Prevent crashes - close clients and threads properly!
    void OnDisable()
    {
        if (receiveThread != null)
            receiveThread.Abort();

        client.Close();
    }

}